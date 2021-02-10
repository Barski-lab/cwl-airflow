from cwl_airflow.components.test.conformance import run_test_conformance
from cwl_airflow.components.test.vulnerability import run_test_vulnerability


def select_test_mode(args):
    """
    Based on the args.conformance or args.vulnerability runs
    either conformance or vulnerability test. As the argument
    group for conformance and vulnerability tests is required
    we can check only one of the parameters.
    """

    if args.conformance:
        run_test_conformance(args)
    else:
        run_test_vulnerability(args)