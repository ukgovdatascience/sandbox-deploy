import subprocess

output = subprocess.run(['./deployer/deploy.sh'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
print(output.stdout)
