import sys
from urllib.parse import urlparse
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.urls import reverse, NoReverseMatch


class Command(BaseCommand):
    help = 'Validate SSLCOMMERZ configuration, environment variables, and callback URLs safely without exposing secrets.'

    def handle(self, *args, **options):
        self.stdout.write("=" * 65)
        self.stdout.write("   NIT HOME — SSLCOMMERZ PAYMENT CONFIGURATION DIAGNOSTIC")
        self.stdout.write("=" * 65)

        issues = []
        warnings = []

        # 1. Environment & Mode
        is_sandbox = getattr(settings, 'SSLCOMMERZ_IS_SANDBOX', True)
        if is_sandbox:
            self.stdout.write(self.style.SUCCESS("[+] SSLCOMMERZ Mode         : SANDBOX (ENABLED)"))
        else:
            self.stdout.write(self.style.WARNING("[!] SSLCOMMERZ Mode         : LIVE PRODUCTION (CAUTION)"))

        debug_mode = getattr(settings, 'DEBUG', True)
        self.stdout.write(f"[*] Django DEBUG Mode       : {debug_mode}")

        # 2. Store ID check
        store_id = getattr(settings, 'SSLCOMMERZ_STORE_ID', '')
        if store_id:
            self.stdout.write(self.style.SUCCESS("[+] Store ID                : CONFIGURED"))
        else:
            self.stdout.write(self.style.ERROR("[-] Store ID                : MISSING (Variable: SSLCOMMERZ_STORE_ID)"))
            issues.append("SSLCOMMERZ_STORE_ID is missing in your environment.")

        # 3. Store Password check (NEVER print value)
        store_pass = getattr(settings, 'SSLCOMMERZ_STORE_PASS', '')
        if store_pass:
            self.stdout.write(self.style.SUCCESS("[+] Store Password          : CONFIGURED"))
        else:
            self.stdout.write(self.style.ERROR("[-] Store Password          : MISSING (Variable: SSLCOMMERZ_STORE_PASS)"))
            issues.append("SSLCOMMERZ_STORE_PASS is missing in your environment.")

        # 4. SITE_URL check
        site_url = getattr(settings, 'SITE_URL', '').rstrip('/')
        if site_url:
            self.stdout.write(self.style.SUCCESS(f"[+] SITE_URL                : CONFIGURED ({site_url})"))
            parsed = urlparse(site_url)
            is_localhost = parsed.hostname in ('localhost', '127.0.0.1', '0.0.0.0')

            if not is_sandbox and parsed.scheme != 'https':
                self.stdout.write(self.style.ERROR("[-] Production HTTPS Check  : FAILED (Production requires https://)"))
                issues.append("In production mode, SITE_URL must use https:// scheme.")

            if is_localhost:
                warnings.append(
                    "SITE_URL points to localhost (127.0.0.1). Note that SSLCOMMERZ's external servers "
                    "cannot send asynchronous IPN webhooks to a local address. For end-to-end IPN testing, "
                    "use a secure public HTTPS development tunnel (e.g. ngrok/Cloudflare) or a staging deployment."
                )
        else:
            self.stdout.write(self.style.ERROR("[-] SITE_URL                : MISSING (Variable: SITE_URL)"))
            issues.append("SITE_URL is missing in your environment.")

        # 5. Verify URL Reverse Resolution
        self.stdout.write("\n" + "-" * 65)
        self.stdout.write("   PAYMENT ROUTE REVERSE RESOLUTION")
        self.stdout.write("-" * 65)

        test_order_num = "TEST12345"
        routes_to_test = [
            ('Initiate Route', 'payments:sslcommerz_initiate', {'order_number': test_order_num}),
            ('IPN Webhook Route', 'payments:sslcommerz_ipn', {}),
            ('Success Route', 'payments:sslcommerz_success', {'order_number': test_order_num}),
            ('Fail Route', 'payments:sslcommerz_fail', {'order_number': test_order_num}),
            ('Cancel Route', 'payments:sslcommerz_cancel', {'order_number': test_order_num}),
        ]

        for label, view_name, kwargs in routes_to_test:
            try:
                resolved_path = reverse(view_name, kwargs=kwargs)
                full_url = f"{site_url}{resolved_path}" if site_url else resolved_path
                self.stdout.write(self.style.SUCCESS(f"[+] {label:<22} : {full_url}"))
            except NoReverseMatch as e:
                self.stdout.write(self.style.ERROR(f"[-] {label:<22} : FAILED TO RESOLVE ({e})"))
                issues.append(f"Failed to reverse route '{view_name}': {e}")

        # Summary & Warnings
        self.stdout.write("\n" + "=" * 65)
        if warnings:
            self.stdout.write(self.style.WARNING("\nINFORMATIONAL NOTICES:"))
            for w in warnings:
                self.stdout.write(f"  * {w}")

        if issues:
            self.stdout.write(self.style.ERROR(f"\nCONFIGURATION INCOMPLETE ({len(issues)} issue(s) detected):"))
            for err in issues:
                self.stdout.write(self.style.ERROR(f"  x {err}"))
            self.stdout.write("\nPlease set the required variables in your .env file.")
            raise CommandError(f"Payment configuration check failed with {len(issues)} issue(s).")
        else:
            self.stdout.write(self.style.SUCCESS("\nCONFIGURATION STATUS: READY FOR PAYMENT FLOW TESTING"))
