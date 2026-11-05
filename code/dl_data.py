import subprocess, sys, os
result = subprocess.run(
    [sys.executable, "-m", "freqtrade", "download-data",
     "--days", "15",
     "--timeframe", "5m"],
    capture_output=True, text=True, cwd=r"C:\Users\Lenovo\Downloads\freqtrade"
)
with open(r"C:\Users\Lenovo\AppData\Local\Temp\opencode\dl_result.txt", "w") as f:
    f.write(result.stdout)
    f.write(result.stderr)
print("DONE")
