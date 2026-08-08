from django.test.runner import DiscoverRunner


class SmartOpsTestRunner(DiscoverRunner):
    """
    Custom Django test runner for SmartOps.

    Enforces app-level test discovery for apps in `apps/` directory to prevent
    duplicate module loading (e.g. `apps.organizations.tests` vs `organizations.tests`).
    """

    LOCAL_APPS = [
        'authentication',
        'organizations',
        'billing',
        'ai_services',
        'dashboard',
    ]

    def build_suite(self, test_labels=None, extra_tests=None, **kwargs):
        if not test_labels:
            test_labels = self.LOCAL_APPS
        return super().build_suite(test_labels=test_labels, extra_tests=extra_tests, **kwargs)
