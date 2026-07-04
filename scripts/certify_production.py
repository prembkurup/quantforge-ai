from quantforge.infrastructure import CertificationDomain, ProductionCertificationEngine


def main() -> None:
    result = ProductionCertificationEngine().certify()
    domain_map = {domain.domain: domain for domain in result.domains}

    print("Production Certification")
    print()
    print("Research")
    print(domain_map[CertificationDomain.RESEARCH].status.value)
    print()
    print("Strategy")
    print(domain_map[CertificationDomain.STRATEGY].status.value)
    print()
    print("Infrastructure")
    print(domain_map[CertificationDomain.INFRASTRUCTURE].status.value)
    print()
    print("Operations")
    print(domain_map[CertificationDomain.OPERATIONS].status.value)
    print()
    print("Risk")
    print(domain_map[CertificationDomain.RISK].status.value)
    print()
    print("Security")
    print(domain_map[CertificationDomain.SECURITY].status.value)
    print()
    print("Performance")
    print(domain_map[CertificationDomain.PERFORMANCE].status.value)
    print()
    print("Governance")
    print(domain_map[CertificationDomain.GOVERNANCE].status.value)
    print()
    print("Score")
    print(f"{result.score.overall:.0f}%")
    print()
    print("Decision")
    print(result.approval.decision.value)
    print()
    print("Live Trading Approval")
    print("AUTHORIZED" if result.approval.authorized else "BLOCKED")


if __name__ == "__main__":
    from quantforge.observability import run_script

    run_script(main, __file__)
