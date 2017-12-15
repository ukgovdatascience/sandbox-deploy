# Sandbox deploy

A service that can talk to a [Data Science Sandbox system](https://github.com/ukgovdatascience/data-science-sandbox-infrastucture) (that is running on Kubernetes) and can get it to deploy sandboxes for new users, and other operations. This service's main interface is an API, that is designed to be talked to by [sandbox-mgt](https://github.com/alphagov/sandbox-mgt).

## Developer setup

### Kubernetes clients

You need kubernetes clients kubectl and helm set-up with credentials to access the k8s cluster.

This guide installs things to your local path `~/sandbox` - adjust paths as necessary.

Clone the infrastructure repo that contains the credentials
```
cd ~/sandbox
git clone https://github.com/ukgovdatascience/data-science-sandbox-infrastucture.git
```

Follow the instructions in that repo's README to get your PGP/GPG key added to the repo's git-crypt auth file. Now you can decrypt the helm chart config in data-science-sandbox-infrastucture/chart-env-config/sandbox/*.yml:
```
brew install git-crypt
cd ~/sandbox/data-science-sandbox-infrastucture
git-crypt unlock
```

Now install kubectl:
```
brew install kubectl  # or on ubuntu we do: sudo snap install kubectl --classic
```
For kubectl to talk to k8s we to use kops to get the secret from S3 and write out `~/.kube/config`.
First Dan gives you access to the S3 bucket. Then:
```
brew install kops
export KOPS_STATE_STORE=s3://kops.data-science.org.uk
export KOPS_NAME=sandbox.data-science.org.uk
kops export kubecfg --name sandbox.data-science.org.uk
# creates ~/.kube/config used by kubectl
kubectl config set-cluster default-cluster --server=https://dashboard.services.sandbox.data-science.org.uk
```

Now this should list the sandboxes:
```
kubectl get namespaces
```

Kubectl gives fundamental access to k8s. Now we install 'helm' which is a higher level interface - it deals in 'charts' which are packages, making it easy to install and configure bunches of k8s resources, such as rstudio.

We need old version of helm, to match the version on our k8s cluster.
```
DESIRED_VERSION=v2.3.0 bash -c 'curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get | bash'
# helm installed into /usr/local/bin/helm
helm init
```

We need a helm chart that MOJ provides - it is more up to date than the one in our fork:
```
helm repo add mojanalytics https://ministryofjustice.github.io/analytics-platform-helm-charts/charts/
```

Playing with sandboxes using helm:
```
export KUBECONFIG=~/.kube/config
export USERNAME=johnsmith
export EMAIL=john.smith@<domain>.gov.uk
export FULLNAME=John Smith
export PLATFORM_ENV=sandbox
export HELM=helm
cd ~/sandbox/data-science-sandbox-infrastucture

e.g.
$HELM delete init-user-${USERNAME} --purge
$HELM delete ${USERNAME}-rstudio --purge
```

### This repo

Clone this repo:
```
cd ~/sandbox
git clone https://github.com/ukgovdatascience/sandbox-deploy.git
```

Create a virtualenv:
```
mkvirtualenv --python=/usr/local/bin/python3 sandbox-deploy
```
Edit ~/.virtualenvs/sandbox-deploy/bin/postactivate so it contains:
```
cd ~/sandbox/sandbox-deploy
export FLASK_APP=deploy/deploy.py
export FLASK_DEBUG=true
export SANDBOX_DEPLOY_USERNAME=
```
Install the dependencies etc:
```
workon sandbox-deploy
pip install -r requirements.txt
```

### Use this repo

Always activate the environment:
```
workon sandbox-deploy
```
Then run commands like this:
```
python3 deploy/commands.py list
python3 deploy/commands.py pod_statuses
python3 deploy/commands.py deploy --username=davidread --email='david.read@<domain>.gov.uk' --fullname='D Read'
```

To run the deploy app:
```
workon sandbox-deploy
flask run --port 7000
```

## Deployment to EC2

```
# if you're not on a GDS IP you need to join the GDS VPN
ssh -i "~/.ssh/dread-data-science-aws.pem" ubuntu@ec2-35-176-150-167.eu-west-2.compute.amazonaws.com
git clone https://github.com/ukgovdatascience/sandbox-deploy.git
git clone https://github.com/ukgovdatascience/data-science-sandbox-infrastucture.git
sudo snap install kubectl --classic
# 2017-08-24T17:29:52Z INFO cannot auto connect core:core-support-plug to core:core-support:
# (slot auto-connection), existing connection state "core:core-support-plug core:core-support" in the way
# kubectl 1.7.0 from 'canonical' installed
mkdir ~/.kube
# run locally:
rsync -e "ssh -i ~/.ssh/dread-data-science-aws.pem" ~/.kube/sandbox.data-science.org.uk ubuntu@ec2-35-176-150-167.eu-west-2.compute.amazonaws.com:~/.kube/config
rsync -e "ssh -i ~/.ssh/dread-data-science-aws.pem" ~/sandbox/data-science-sandbox-infrastucture/chart-env-config/sandbox/*.yml ubuntu@ec2-35-176-150-167.eu-west-2.compute.amazonaws.com:~/data-science-sandbox-infrastucture/chart-env-config/sandbox/
# run on the EC2 box:
kubectl config set-cluster default-cluster --server=https://dashboard.services.sandbox.data-science.org.uk
DESIRED_VERSION=v2.7.2 bash -c 'curl https://raw.githubusercontent.com/kubernetes/helm/master/scripts/get | bash'
# helm installed into /usr/local/bin/helm
helm init
helm repo add mojanalytics https://ministryofjustice.github.io/analytics-platform-helm-charts/charts/
export PLATFORM_ENV=sandbox
export CHART_ENV_CONFIG=../data-science-sandbox-infrastucture/chart-env-config
export HELM=helm
export SANDBOX_DEPLOY_USERNAME=deploy
export SANDBOX_DEPLOY_PASSWORD=<password>
curl -O https://bootstrap.pypa.io/get-pip.py
python3 get-pip.py
rm get-pip.py
pip install virtualenv
virtualenv ~/venv
. ~/venv/bin/activate
cd ~/sandbox-deploy
pip install -r requirements.txt
pip install gunicorn

export FLASK_APP=deploy/deploy.py
flask run --port 7000  # just to check it runs

sudo apt-get install nginx
sudo vim /etc/nginx/conf.d/deploy.conf && sudo systemctl reload nginx
  server {
    listen       80;
    server_name  localhost .compute.amazonaws.com deploy.sandbox.data-science.org.uk;
    location / {
        proxy_pass http://127.0.0.1:8000;
    }
  }
sudo systemctl reload nginx
sudo systemctl status nginx

. ~/venv/bin/activate
cd ~/sandbox-deploy
# export env variables (see above)
gunicorn deploy.deploy:app -b localhost:8000 &
# in AWS dashboard change security group to allow ports 80 & 443 from anywhere
# browse: http://ec2-35-176-150-167.eu-west-2.compute.amazonaws.com

# get (sub)domain using AWS Route53
deploy.sandbox.data-science.org.uk.  CNAME  ec2-35-176-150-167.eu-west-2.compute.amazonaws.com

# Setup letsencrypt cert: https://certbot.eff.org/#ubuntuxenial-nginx )
sudo apt-get update
sudo apt-get install software-properties-common
sudo add-apt-repository ppa:certbot/certbot
sudo apt-get update
sudo apt-get install python-certbot-nginx
sudo certbot --nginx
# domain name(s): 1 (deploy.sandbox.data-science.org.uk)
# redirect HTTP traffic to HTTPS, removing HTTP access: 2 (yes)
# browse: https://deploy.sandbox.data-science.org.uk
$ sudo vim /etc/cron.d/certbot
# Add --renew-hook bit to the last line:
  0 */12 * * * root test -x /usr/bin/certbot && perl -e 'sleep int(rand(3600))' && certbot -q renew --renew-hook "/etc/init.d/nginx reload"
```

## Redeploy updates to EC2
```
ssh -i "~/.ssh/dread-data-science-aws.pem" ubuntu@ec2-35-176-150-167.eu-west-2.compute.amazonaws.com
cd ~/sandbox-deploy
git pull
. ~/venv/bin/activate
export PLATFORM_ENV=sandbox
export CHART_ENV_CONFIG=../data-science-sandbox-infrastucture/chart-env-config
export HELM=helm
export SANDBOX_DEPLOY_USERNAME=deploy
export SANDBOX_DEPLOY_PASSWORD=<password>
killall gunicorn
gunicorn deploy.deploy:app -b localhost:8000 &
# Confirm it's running: https://deploy.sandbox.data-science.org.uk/
```
