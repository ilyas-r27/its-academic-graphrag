"""Rule-based reasoning with Z3 (materi Propositional Logic).

Deterministic rules (batas SKS, syarat evaluasi studi, dst.) are answered here, not by the LLM.

WARNING: the thresholds below are EXAMPLE values from the course slides (ppt 01).
Replace them with the actual numbers from the Peraturan Akademik 2025 and cite the pasal.

Usage:
    python -m rules.sks_rules 3.2
    python -m rules.sks_rules --check-conflict
"""
import argparse

from z3 import And, Implies, Int, Real, Solver, sat

SOURCE = "TODO: Pasal ... Peraturan Rektor No. 33 Tahun 2025"

# (lower bound inclusive, upper bound exclusive, max SKS)
SKS_RULES = [
    (0.0, 2.50, 18),
    (2.50, 3.00, 20),
    (3.00, 3.50, 22),
    (3.50, 4.01, 24),
]


def _kb(ips, sks):
    return [Implies(And(ips >= lo, ips < hi), sks == m) for lo, hi, m in SKS_RULES]


def max_sks(ips_value: float) -> int | None:
    ips, sks = Real("ips"), Int("max_sks")
    s = Solver()
    s.add(*_kb(ips, sks), ips == ips_value)
    if s.check() != sat:
        return None
    # entailment check: is any other value possible? (KB and sks != v must be UNSAT)
    v = s.model()[sks].as_long()
    s.push()
    s.add(sks != v)
    entailed = s.check() != sat
    s.pop()
    return v if entailed else None


def check_conflict() -> None:
    """Demo of consistency checking with an unsat core: two sources disagree."""
    sks = Int("max_sks")
    s = Solver()
    s.set(unsat_core=True)
    s.assert_and_track(sks == 24, "peraturan_2025")
    s.assert_and_track(sks == 22, "sistem_frs")
    print(s.check(), s.unsat_core())


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("ips", type=float, nargs="?")
    ap.add_argument("--check-conflict", action="store_true")
    args = ap.parse_args()
    if args.check_conflict:
        check_conflict()
    if args.ips is not None:
        print(f"IPS {args.ips} -> maks {max_sks(args.ips)} SKS ({SOURCE})")


if __name__ == "__main__":
    main()
