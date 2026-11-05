import subprocess, sys, os
result = subprocess.run(
    [sys.executable, "-c", "import freqtrade; print(freqtrade.__file__)"],
    capture_output=True, text=True
)
print("STDOUT:", result.stdout.strip())
print("STDERR:", result.stderr.strip()[:200])
