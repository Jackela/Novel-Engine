## QA Hardening Quickstart

1. **Install prerequisites**
   ```bash
   sudo apt-get update
   sudo apt-get install -y python3.11 python3.11-venv python3-pip docker.io
   curl -s https://raw.githubusercontent.com/nektos/act/master/install.sh | sudo bash -s -- -b /usr/local/bin
   python3 -m pip install --user playwright
   python3 -m playwright install
   ```

2. **Run local validation**
   ```bash
   ./scripts/validate_ci_locally.sh
   ```

3. **Emulate QA workflow**
   ```bash
   act --secret-file .secrets -W .github/workflows/quality_assurance.yml
   ```

4. **Apply formatting (if needed)**
   ```bash
   python3 -m black src tests ai_testing
   python3 -m isort src tests ai_testing
   ```

5. **Run regression tests**
   ```bash
   python3 -m pytest -m "not requires_services" --tb=short
   ```
