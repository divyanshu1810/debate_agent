from llm_guard.input_scanners import Toxicity, PromptInjection
from llm_guard.output_scanners import Toxicity as OutputToxicity, Relevance
from llm_guard import scan_prompt, scan_output as _llm_guard_scan_output

INPUT_SCANNERS  = [Toxicity(), PromptInjection()]
OUTPUT_SCANNERS = [OutputToxicity(), Relevance()]


def scan_input(text: str) -> tuple[str, bool]:
    # scan_prompt returns (sanitized_output, results_valid: dict[str,bool], results_score: dict[str,float])
    sanitized, results_valid, results_score = scan_prompt(INPUT_SCANNERS, text)
    return sanitized, all(results_valid.values())


def scan_output(prompt: str, output: str) -> tuple[str, bool]:
    # alias avoids shadowing the llm_guard import with the same function name
    sanitized, results_valid, results_score = _llm_guard_scan_output(OUTPUT_SCANNERS, prompt, output)
    return sanitized, all(results_valid.values())