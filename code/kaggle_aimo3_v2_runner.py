import contextlib
import gc
import json
import math
import os
import queue
import re
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict, dataclass
from typing import Optional

import pandas as pd
import polars as pl
from jupyter_client import KernelManager
from openai import OpenAI
from openai_harmony import (
    Author,
    Conversation,
    HarmonyEncodingName,
    Message,
    ReasoningEffort,
    Role,
    SystemContent,
    TextContent,
    ToolNamespaceConfig,
    load_harmony_encoding,
)
from transformers import set_seed

import kaggle_evaluation.aimo_3_inference_server


class CFG:
    # Search-method personas (not wording personas)
    system_prompts = [
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Pure algebra derivation with strict symbolic steps.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Invariant/parity reasoning and contradiction.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Modular arithmetic/number theory.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Small-case brute force then prove pattern.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Full enumeration if feasible.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: DP/recursion counting.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: CSP/ILP/SAT modeling and solve.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Graph/state search with BFS/DFS.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Counterexample-first falsification.',
        'You are an IMO competitor. Final answer in \\boxed{}. [STYLE]: Bounds/elimination/pruning.',
    ]

    tir_tooling_block = (
        'When using Python, explicitly use: itertools.product/combinations/permutations, '
        'collections.Counter/defaultdict, functools.lru_cache, sympy.factorint/divisors/solve/diophantine, '
        'math.gcd/mod checks, BFS/DFS templates, ILP/CSP if feasible, and small-case consistency checks.'
    )

    verifier_system_prompt = (
        'You are a strict Mathematical Auditor. Verify by plugging proposed answer into constraints. '
        'Write Python verification code with explicit assert statements and non-trivial checks. '
        'Do not use tautologies. If a decisive check cannot be established, keep verification weak (UNVERIFIED).'
    )
    verifier_counterexample_prompt = (
        'You are a strict Mathematical Auditor. Try to falsify the proposed answer. '
        'Find at least one contradiction, impossible condition, or mismatch via Python assertions. '
        'If no decisive falsification/proof is available, treat it as UNVERIFIED rather than VALID.'
    )

    tool_prompt = 'Use this tool to execute Python code. The environment is a stateful Jupyter notebook. Use print().'
    preference_prompt = 'You have access to `math`, `numpy`, and `sympy`.'

    served_model_name = 'gpt-oss'
    model_path = '/kaggle/input/models/danielhanchen/gpt-oss-120b/transformers/default/1'
    kv_cache_dtype = 'fp8_e4m3'
    dtype = 'auto'

    high_problem_timeout, base_problem_timeout = 420, 200
    notebook_limit, server_timeout = 21600, 180
    session_timeout, jupyter_timeout, sandbox_timeout = 960, 6, 3
    context_tokens, buffer_tokens = 65536, 512

    top_logprobs, batch_size, attempts, workers, turns = 10, 256, 10, 10, 128
    attempts_variants = [10, 16, 20]

    gpu_memory_utilization, temperature, min_p, seed = 0.96, 1.0, 0.02, 42

    use_counterexample_verifier = True
    verifier_max_rounds = 3


set_seed(CFG.seed)
LOG_DIR = '/kaggle/working/logs'
os.makedirs(f'{LOG_DIR}/recall_eval', exist_ok=True)
os.makedirs(f'{LOG_DIR}/style_eval', exist_ok=True)
os.makedirs(f'{LOG_DIR}/ranker_eval', exist_ok=True)


@dataclass
class VerifierResult:
    verdict: str  # VALID / INVALID / UNVERIFIED
    tool_output: str
    verifier_code: str
    quality_score: float
    uses_candidate_flag: int
    has_nontrivial_assert_flag: int
    condition_reference_flag: int
    contradiction_flag: int
    error_flag: int


class AIMO3Template:
    def get_system_content(self, prompt, tool_cfg):
        return SystemContent.new().with_model_identity(prompt).with_reasoning_effort(
            reasoning_effort=ReasoningEffort.HIGH
        ).with_tools(tool_cfg)

    def apply_chat_template(self, sys_prompt, usr_prompt, tool_cfg):
        return [
            Message.from_role_and_content(Role.SYSTEM, self.get_system_content(sys_prompt, tool_cfg)),
            Message.from_role_and_content(Role.USER, usr_prompt),
        ]


class AIMO3Sandbox:
    _port_lock = threading.Lock()
    _base_port = int(time.time() % 10000) + 40000

    @classmethod
    def _get_next_ports(cls, count=5):
        with cls._port_lock:
            ports = list(range(cls._base_port, cls._base_port + count))
            cls._base_port += count
            return ports

    def __init__(self, timeout):
        self._default_timeout = timeout
        ports = self._get_next_ports(5)
        env = os.environ.copy()
        env.update({'PYDEVD_DISABLE_FILE_VALIDATION': '1', 'MPLBACKEND': 'Agg'})

        self._km = KernelManager()
        self._km.shell_port, self._km.iopub_port, self._km.stdin_port, self._km.hb_port, self._km.control_port = ports
        self._km.start_kernel(env=env, extra_arguments=['--Application.log_level=CRITICAL'])
        self._client = self._km.blocking_client()
        self._client.start_channels()
        self._client.wait_for_ready(timeout=self._default_timeout)

        self.execute(
            'import sys\n'
            'sys.set_int_max_str_digits(0)\n'
            'import math, numpy, sympy, mpmath, itertools, collections, fractions, functools\n'
            'mpmath.mp.dps = 64\n'
        )

    def _format_error(self, tb):
        return ''.join(re.sub(r'\x1b\[[0-9;]*m', '', f) for f in tb if 'File "' not in f or 'ipython-input' in f)

    def execute(self, code, timeout=None):
        effective_timeout = timeout or self._default_timeout
        msg_id = self._client.execute(code, store_history=True, allow_stdin=False, stop_on_error=False)

        stdout, stderr, start = [], [], time.time()
        while True:
            if time.time() - start > effective_timeout:
                self._km.interrupt_kernel()
                return '[ERROR] Timeout'
            try:
                msg = self._client.get_iopub_msg(timeout=1.0)
            except queue.Empty:
                continue

            if msg.get('parent_header', {}).get('msg_id') != msg_id:
                continue

            mt, c = msg.get('msg_type'), msg.get('content', {})
            if mt == 'stream':
                if c.get('name') == 'stdout':
                    stdout.append(c.get('text', ''))
                else:
                    stderr.append(c.get('text', ''))
            elif mt == 'error':
                stderr.append(self._format_error(c.get('traceback', [])))
            elif mt in {'execute_result', 'display_data'}:
                txt = c.get('data', {}).get('text/plain')
                if txt:
                    stdout.append(txt if txt.endswith('\n') else f'{txt}\n')
            elif mt == 'status' and c.get('execution_state') == 'idle':
                break

        out, err = ''.join(stdout), ''.join(stderr)
        if err and out:
            return f'{out.rstrip()}\n{err}'
        return err or out or '[WARN] No output.'

    def close(self):
        with contextlib.suppress(Exception):
            self._client.stop_channels()
        with contextlib.suppress(Exception):
            self._km.shutdown_kernel(now=True)
        with contextlib.suppress(Exception):
            self._km.cleanup_resources()

    def reset(self):
        self.execute('%reset -f\nimport sys\nsys.set_int_max_str_digits(0)\nimport math, numpy, sympy\n')


class AIMO3Tool:
    def __init__(self, timeout, prompt, sandbox):
        self._local_jupyter_timeout = timeout
        self._tool_prompt = prompt
        self._jupyter_session = sandbox
        self._execution_lock = threading.Lock()

    def _ensure_last_print(self, code):
        lines = code.strip().split('\n')
        if not lines:
            return code
        last = lines[-1].strip()
        if any(x in last for x in ['print', 'import']) or not last or last.startswith('#'):
            return code
        lines[-1] = 'print(' + last + ')'
        return '\n'.join(lines)

    @property
    def instruction(self):
        return self._tool_prompt

    @property
    def tool_config(self):
        return ToolNamespaceConfig(name='python', description=self.instruction, tools=[])

    def process_sync_plus(self, message):
        final_script = self._ensure_last_print(message.content[0].text)
        with self._execution_lock:
            output = self._jupyter_session.execute(final_script, timeout=self._local_jupyter_timeout)
        msg = Message(author=Author(role=Role.TOOL, name='python'), content=[TextContent(text=output)]).with_recipient('assistant')
        return [msg.with_channel(message.channel) if message.channel else msg]


class AIMO3Solver:
    def __init__(self, cfg, port=8000):
        self.cfg = cfg
        self.port = port
        self.base_url, self.api_key = f'http://0.0.0.0:{port}/v1', 'sk-local'

        self.template = AIMO3Template()
        self.encoding = load_harmony_encoding(HarmonyEncodingName.HARMONY_GPT_OSS)
        self.stop_token_ids = self.encoding.stop_tokens_for_assistant_actions()

        self._preload_model_weights()
        self.server_process = self._start_server()
        self.client = OpenAI(base_url=self.base_url, api_key=self.api_key, timeout=self.cfg.session_timeout)
        self._wait_for_server()
        self._initialize_kernels()

        self.notebook_start_time = time.time()
        self.problems_remaining = 50

    def _preload_model_weights(self):
        files = []
        for r, _, fs in os.walk(self.cfg.model_path):
            for f in fs:
                p = os.path.join(r, f)
                if os.path.isfile(p):
                    files.append(p)
        with ThreadPoolExecutor(max_workers=self.cfg.workers) as ex:
            list(ex.map(lambda p: open(p, 'rb').read(1), files))

    def _start_server(self):
        cmd = [
            sys.executable, '-m', 'vllm.entrypoints.openai.api_server',
            '--seed', str(self.cfg.seed),
            '--model', self.cfg.model_path,
            '--served-model-name', self.cfg.served_model_name,
            '--tensor-parallel-size', '1',
            '--max-num-seqs', str(self.cfg.batch_size),
            '--gpu-memory-utilization', str(self.cfg.gpu_memory_utilization),
            '--port', str(self.port),
            '--dtype', self.cfg.dtype,
            '--kv-cache-dtype', self.cfg.kv_cache_dtype,
            '--disable-log-stats', '--enable-prefix-caching',
        ]
        self.log_file = open('vllm_server.log', 'w')
        return subprocess.Popen(cmd, stdout=self.log_file, stderr=subprocess.STDOUT, start_new_session=True)

    def _wait_for_server(self):
        for _ in range(self.cfg.server_timeout):
            if self.server_process.poll() is not None:
                raise RuntimeError('vLLM server died.')
            try:
                self.client.models.list()
                return
            except Exception:
                time.sleep(1)
        raise RuntimeError('vLLM server timeout.')

    def _initialize_kernels(self):
        self.sandbox_pool = queue.Queue()
        with ThreadPoolExecutor(max_workers=self.cfg.workers) as ex:
            futures = [ex.submit(lambda: AIMO3Sandbox(timeout=self.cfg.jupyter_timeout)) for _ in range(self.cfg.workers)]
            for future in as_completed(futures):
                self.sandbox_pool.put(future.result())

    def _scan_for_answer(self, text):
        patterns = [r'\\boxed\s*\{\s*([0-9,]+)\s*\}', r'final\s+answer\s+is\s*([0-9,]+)']
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                try:
                    val = int(matches[-1].replace(',', ''))
                    if 0 <= val <= 99999:
                        return val
                except ValueError:
                    pass
        return None

    def _compute_mean_entropy(self, logprobs):
        if not logprobs:
            return float('inf')
        entropies = []
        for top in logprobs:
            if top:
                e = sum(-math.exp(lp) * math.log2(max(math.exp(lp), 1e-12)) for lp in top.values() if math.exp(lp) > 0)
                entropies.append(e)
        return sum(entropies) / len(entropies) if entropies else float('inf')

    def _evaluate_verifier_quality(self, problem, candidate_ans, verifier_code):
        code = verifier_code or ''
        compact = re.sub(r'\s+', '', code.lower())

        uses_candidate = str(candidate_ans) in code
        has_assert = 'assert' in compact
        tautology = any(t in compact for t in ['asserttrue', 'assert1==1', 'assert0==0'])
        tautology = tautology or bool(re.search(r'assert([^=<>!]+)==\1', compact))
        has_nontrivial_assert = has_assert and not tautology

        problem_tokens = {tok for tok in re.findall(r'[a-zA-Z]{3,}', problem.lower()) if len(tok) > 3}
        code_tokens = set(re.findall(r'[a-zA-Z]{3,}', code.lower()))
        condition_reference = len(problem_tokens.intersection(code_tokens)) >= 2

        score = 0.0
        score += 0.30 if uses_candidate else 0.0
        score += 0.25 if has_assert else 0.0
        score += 0.25 if has_nontrivial_assert else 0.0
        score += 0.20 if condition_reference else 0.0
        return {
            'quality_score': round(score, 4),
            'uses_candidate_flag': int(uses_candidate),
            'has_nontrivial_assert_flag': int(has_nontrivial_assert),
            'condition_reference_flag': int(condition_reference),
        }

    def _classify_verdict(self, tool_output, quality, contradiction_found):
        err = any(x in (tool_output or '') for x in ['[ERROR]', 'Traceback', 'AssertionError', 'Error:'])
        if err or contradiction_found:
            return 'INVALID', int(err)
        if quality['quality_score'] >= 0.75 and quality['uses_candidate_flag'] == 1 and quality['has_nontrivial_assert_flag'] == 1:
            return 'VALID', 0
        return 'UNVERIFIED', 0

    def _verify_candidate(self, problem, candidate_ans):
        verifier_prompt = self.cfg.verifier_counterexample_prompt if self.cfg.use_counterexample_verifier else self.cfg.verifier_system_prompt
        verifier_input = f'Problem: {problem}\nProposed Answer: {candidate_ans}\nProvide Python verification code.'

        sandbox = None
        tool_output, verifier_code = '', ''
        contradiction_found = False

        quality = {
            'quality_score': 0.0,
            'uses_candidate_flag': 0,
            'has_nontrivial_assert_flag': 0,
            'condition_reference_flag': 0,
        }

        try:
            sandbox = self.sandbox_pool.get(timeout=self.cfg.sandbox_timeout)
            local_tool = AIMO3Tool(self.cfg.jupyter_timeout, self.cfg.tool_prompt, sandbox)
            conv = Conversation.from_messages(
                self.template.apply_chat_template(verifier_prompt, verifier_input, local_tool.tool_config)
            )

            for _ in range(self.cfg.verifier_max_rounds):
                prompt_ids = self.encoding.render_conversation_for_completion(conv, Role.ASSISTANT)
                max_toks = self.cfg.context_tokens - len(prompt_ids)
                if max_toks < self.cfg.buffer_tokens:
                    break

                stream = self.client.completions.create(
                    model=self.cfg.served_model_name,
                    temperature=0.2,
                    max_tokens=max_toks,
                    prompt=prompt_ids,
                    seed=int(time.time()),
                    stream=True,
                    extra_body={
                        'min_p': self.cfg.min_p,
                        'stop_token_ids': self.stop_token_ids,
                        'return_token_ids': True,
                    },
                )
                tok_buf = []
                for chunk in stream:
                    if chunk.choices[0].token_ids:
                        tok_buf.extend(chunk.choices[0].token_ids)

                if not tok_buf:
                    break

                new_msgs = self.encoding.parse_messages_from_completion_tokens(tok_buf, Role.ASSISTANT)
                conv.messages.extend(new_msgs)
                last = new_msgs[-1]

                if last.recipient == 'python':
                    verifier_code = last.content[0].text
                    quality = self._evaluate_verifier_quality(problem, candidate_ans, verifier_code)
                    if quality['has_nontrivial_assert_flag'] == 0:
                        tool_output = '[ERROR] Weak or tautology verifier'
                        break

                    resp = local_tool.process_sync_plus(last)
                    tool_output = resp[0].content[0].text
                    contradiction_found = 'mismatch' in tool_output.lower() or 'contradiction' in tool_output.lower()
                    conv.messages.extend(resp)
                    break
        except Exception as exc:
            tool_output = f'[ERROR] {exc}'
        finally:
            if sandbox is not None:
                sandbox.reset()
                self.sandbox_pool.put(sandbox)

        verdict, error_flag = self._classify_verdict(tool_output, quality, contradiction_found)
        return VerifierResult(
            verdict=verdict,
            tool_output=tool_output,
            verifier_code=verifier_code,
            quality_score=quality['quality_score'],
            uses_candidate_flag=quality['uses_candidate_flag'],
            has_nontrivial_assert_flag=quality['has_nontrivial_assert_flag'],
            condition_reference_flag=quality['condition_reference_flag'],
            contradiction_flag=int(contradiction_found),
            error_flag=error_flag,
        )

    def _small_case_consistency_score(self, problem_text, answer):
        _ = (problem_text, answer)
        return 0.0

    def _process_attempt(self, problem, idx, stop_evt, deadline):
        if stop_evt.is_set() or time.time() > deadline:
            return {
                'Attempt': idx + 1,
                'Answer': None,
                'Entropy': float('inf'),
                'Style': 'Skipped',
                'style_name': 'Skipped',
                'is_tir': 0,
                'used_python': 0,
                'python_output_nonempty': 0,
                'python_error': 0,
            }

        base_prompt = self.cfg.system_prompts[idx % len(self.cfg.system_prompts)]
        is_tir = int(any(k in base_prompt.lower() for k in ['brute force', 'enumeration', 'dp', 'search', 'csp', 'ilp']))
        sys_prompt = base_prompt + (' ' + self.cfg.tir_tooling_block if is_tir else '')

        sandbox = None
        ans, logprobs = None, []
        used_python = 0
        python_output_nonempty = 0
        python_error = 0
        seed = int(math.pow(self.cfg.seed + idx, 2))

        try:
            sandbox = self.sandbox_pool.get(timeout=self.cfg.sandbox_timeout)
            local_tool = AIMO3Tool(self.cfg.jupyter_timeout, self.cfg.tool_prompt, sandbox)
            conv = Conversation.from_messages(self.template.apply_chat_template(sys_prompt, problem, local_tool.tool_config))

            for _ in range(self.cfg.turns):
                if stop_evt.is_set() or time.time() > deadline:
                    break

                prompt_ids = self.encoding.render_conversation_for_completion(conv, Role.ASSISTANT)
                max_toks = self.cfg.context_tokens - len(prompt_ids)
                if max_toks < self.cfg.buffer_tokens:
                    break

                stream = self.client.completions.create(
                    model=self.cfg.served_model_name,
                    temperature=self.cfg.temperature,
                    logprobs=self.cfg.top_logprobs,
                    max_tokens=max_toks,
                    prompt=prompt_ids,
                    seed=seed,
                    stream=True,
                    extra_body={
                        'min_p': self.cfg.min_p,
                        'stop_token_ids': self.stop_token_ids,
                        'return_token_ids': True,
                    },
                )

                tok_buf, txt_chunks = [], []
                for chunk in stream:
                    if stop_evt.is_set() or time.time() > deadline:
                        break
                    if chunk.choices[0].token_ids:
                        tok_buf.extend(chunk.choices[0].token_ids)
                        txt_chunks.append(chunk.choices[0].text)
                        if chunk.choices[0].logprobs:
                            logprobs.extend(chunk.choices[0].logprobs.top_logprobs)
                    if '}' in chunk.choices[0].text:
                        ans = self._scan_for_answer(''.join(txt_chunks[-32:]))
                        if ans is not None:
                            break

                if ans is not None or not tok_buf:
                    break

                new_msgs = self.encoding.parse_messages_from_completion_tokens(tok_buf, Role.ASSISTANT)
                conv.messages.extend(new_msgs)
                last = new_msgs[-1]

                if last.channel == 'final':
                    ans = self._scan_for_answer(last.content[0].text)
                    break

                if last.recipient == 'python':
                    used_python = 1
                    resp = local_tool.process_sync_plus(last)
                    out = resp[0].content[0].text
                    python_output_nonempty = int(bool(out and out.strip()))
                    python_error = int(any(x in out for x in ['[ERROR]', 'Traceback', 'Error:']))
                    conv.messages.extend(resp)
        except Exception:
            pass
        finally:
            if sandbox is not None:
                sandbox.reset()
                self.sandbox_pool.put(sandbox)

        style_name = self.cfg.system_prompts[idx % len(self.cfg.system_prompts)]
        return {
            'Attempt': idx + 1,
            'Entropy': self._compute_mean_entropy(logprobs),
            'Answer': ans,
            'Style': f'Style {idx % len(self.cfg.system_prompts)}',
            'style_name': style_name,
            'is_tir': is_tir,
            'used_python': used_python,
            'python_output_nonempty': python_output_nonempty,
            'python_error': python_error,
        }

    def _select_answer(self, results, problem_text, gold_answer, prob_id):
        ans_weights = defaultdict(float)
        ans_votes = defaultdict(int)
        valid_candidates = []

        for r in results:
            if r['Answer'] is not None:
                a = r['Answer']
                valid_candidates.append(a)
                base_weight = 1.0 / max(r['Entropy'], 1e-9)
                ans_weights[a] += base_weight
                ans_votes[a] += 1

        scored = sorted(
            [{'answer': a, 'votes': ans_votes[a], 'base_score': w} for a, w in ans_weights.items()],
            key=lambda x: x['base_score'],
            reverse=True,
        )

        recall_hit = 1 if (gold_answer is not None and gold_answer in valid_candidates) else 0
        majority_answer = Counter(valid_candidates).most_common(1)[0][0] if valid_candidates else None
        majority_correct = 1 if (gold_answer is not None and majority_answer == gold_answer) else 0

        ranking_scores = []
        best_ans = 0
        highest_composite = -float('inf')

        verifier_bonus_map = {'VALID': 0.40, 'UNVERIFIED': 0.10, 'INVALID': -0.20}
        majority_bonus = 0.0

        for cand in scored:
            ans = cand['answer']
            v = self._verify_candidate(problem_text, ans)
            verifier_bonus = verifier_bonus_map.get(v.verdict, 0.0)
            small_score = self._small_case_consistency_score(problem_text, ans)
            composite_score = cand['base_score'] + verifier_bonus + (majority_bonus if ans == majority_answer else 0.0) + small_score

            ranking_scores.append({
                'answer': ans,
                'votes': cand['votes'],
                'base_score': cand['base_score'],
                'majority_answer_flag': int(ans == majority_answer),
                'verifier_verdict': v.verdict,
                'verifier_bonus': verifier_bonus,
                'small_case_consistency_score': small_score,
                'composite_score': composite_score,
                'selected_flag': 0,
                'verifier_quality_score': v.quality_score,
                'uses_candidate_flag': v.uses_candidate_flag,
                'has_nontrivial_assert_flag': v.has_nontrivial_assert_flag,
                'condition_reference_flag': v.condition_reference_flag,
                'contradiction_flag': v.contradiction_flag,
                'error_flag': v.error_flag,
            })

            if composite_score > highest_composite:
                highest_composite = composite_score
                best_ans = ans

        for row in ranking_scores:
            row['selected_flag'] = int(row['answer'] == best_ans)

        selected_correct = 1 if (gold_answer is not None and best_ans == gold_answer) else 0

        summary = {
            'problem_id': prob_id,
            'attempts': len(results),
            'gold_answer': gold_answer,
            'candidate_answers': list(set(valid_candidates)),
            'recall_at_k_hit': recall_hit,
            'candidate_unique_count': len(set(valid_candidates)),
            'majority_answer': majority_answer,
            'majority_is_correct': majority_correct,
            'ranking_selector_answer': best_ans,
            'ranking_is_correct': selected_correct,
        }

        with open(f'{LOG_DIR}/recall_eval/recall_summary.jsonl', 'a') as f:
            f.write(json.dumps(summary) + '\n')

        with open(f'{LOG_DIR}/ranker_eval/per_problem_candidate_scores.jsonl', 'a') as f:
            f.write(json.dumps({'problem_id': prob_id, 'ranking_scores': ranking_scores}) + '\n')

        return best_ans

    def _allocate_budget(self, attempts):
        time_left = self.cfg.notebook_limit - (time.time() - self.notebook_start_time)
        raw_budget = max(
            self.cfg.base_problem_timeout,
            min(time_left - max(0, self.problems_remaining - 1) * self.cfg.base_problem_timeout, self.cfg.high_problem_timeout),
        )
        per_attempt = raw_budget / max(1, 10)
        scaled = per_attempt * max(1, attempts)
        return min(self.cfg.high_problem_timeout, max(self.cfg.base_problem_timeout, scaled))

    def solve_problem(self, problem, gold_answer=None, prob_id=None, attempts_override=None):
        attempts = attempts_override or self.cfg.attempts
        budget = self._allocate_budget(attempts)
        deadline = time.time() + budget

        results = []
        stop_evt = threading.Event()

        with ThreadPoolExecutor(max_workers=self.cfg.workers) as ex:
            futures = [ex.submit(self._process_attempt, problem, i, stop_evt, deadline) for i in range(attempts)]
            for future in as_completed(futures):
                try:
                    results.append(future.result())
                except Exception:
                    pass

        self.problems_remaining = max(0, self.problems_remaining - 1)

        per_attempt_rows = []
        for r in results:
            per_attempt_rows.append({
                'problem_id': prob_id,
                'domain': str(prob_id).split('-')[2] if isinstance(prob_id, str) and '-' in str(prob_id) else 'unknown',
                'attempt_idx': r['Attempt'],
                'style_name': r['style_name'],
                'is_tir': r['is_tir'],
                'answer': r['Answer'],
                'answer_is_correct': int(gold_answer is not None and r['Answer'] == gold_answer),
                'used_python': r['used_python'],
                'python_error': r['python_error'],
                'entropy': r['Entropy'],
                'verifier_verdict': '',
                'verifier_quality_score': '',
                'selected_final': 0,
            })

        csv_path = f'{LOG_DIR}/style_eval/per_attempt_style.csv'
        header = 'problem_id,domain,attempt_idx,style_name,is_tir,answer,answer_is_correct,used_python,python_error,entropy,verifier_verdict,verifier_quality_score,selected_final\n'
        if not os.path.exists(csv_path):
            with open(csv_path, 'w') as f:
                f.write(header)
        with open(csv_path, 'a') as f:
            for row in per_attempt_rows:
                f.write(','.join(str(row[k]) for k in ['problem_id','domain','attempt_idx','style_name','is_tir','answer','answer_is_correct','used_python','python_error','entropy','verifier_verdict','verifier_quality_score','selected_final']) + '\n')

        return self._select_answer(results, problem, gold_answer, prob_id)


def build_solver_env():
    # Optional wheel bootstrap for Kaggle offline setup.
    archive = '/kaggle/input/notebooks/andreasbis/aimo-3-utils/wheels.tar.gz'
    tmp = '/kaggle/tmp/setup'
    if os.path.exists(archive):
        if not os.path.exists(tmp):
            os.makedirs(tmp, exist_ok=True)
            subprocess.run(['tar', '-xzf', archive, '-C', tmp], check=True)
        subprocess.run([
            sys.executable,
            '-m',
            'pip',
            'install',
            '--no-index',
            '--find-links',
            f'{tmp}/wheels',
            'unsloth',
            'trl',
            'vllm',
            'openai_harmony',
        ], check=True)

    envs = [
        ('TRANSFORMERS_NO_TF', '1'),
        ('TRANSFORMERS_NO_FLAX', '1'),
        ('CUDA_VISIBLE_DEVICES', '0'),
        ('TOKENIZERS_PARALLELISM', 'false'),
        ('TRITON_PTXAS_PATH', '/usr/local/cuda/bin/ptxas'),
        ('TIKTOKEN_ENCODINGS_BASE', '/kaggle/tmp/setup/tiktoken_encodings'),
    ]
    for k, v in envs:
        os.environ[k] = v


def run_kaggle_inference():
    build_solver_env()
    solver = AIMO3Solver(CFG)

    def predict(id_: pl.DataFrame, question: pl.DataFrame, answer: Optional[pl.DataFrame] = None) -> pl.DataFrame:
        gc.disable()
        gold = answer.item(0) if answer is not None else None
        prob_id = id_.item(0)
        final_answer = solver.solve_problem(question.item(0), gold_answer=gold, prob_id=prob_id)
        gc.enable()
        gc.collect()
        return pl.DataFrame({'id': prob_id, 'answer': final_answer})

    inference_server = kaggle_evaluation.aimo_3_inference_server.AIMO3InferenceServer(predict)
    if os.getenv('KAGGLE_IS_COMPETITION_RERUN'):
        inference_server.serve()
    else:
        inference_server.run_local_gateway(('/kaggle/input/datasets/hinemos/imo-data20/imo_bench_data.csv',))


if __name__ == '__main__':
    run_kaggle_inference()
