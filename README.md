# 10Seconds-core

## How to run
### 1. git clone
```bash
git clone https://github.com/JanSound/10Seconds-core.git
```

<br>

### 2. build docker image (m1 기준)
```bash
docker build -t 10seconds-core:latest \
--build-arg AWS_ACCESS_KEY_ID=(aws key id) \
--build-arg AWS_SECRET_ACCESS_KEY=(aws secret access key) \
--platform linux/amd64 .
```

<br>

### 3. upload docker image to AWS ECR
**1) ecr login**
```bash
aws ecr get-login-password --region (region명) | \
docker login --username AWS --password-stdin (ECR 레포지토리 주소)
```
**2) assign tag**
```bash
docker tag 10seconds-core:latest (ECR 레포지토리 주소):10seconds-core
```
**3) push image**
```bash
docker push (ECR 레포지토리 주소):10seconds-core
```

<br>

### 4. run docker image (AWS Linux EC2 기준)
**1) ecr login**
```bash
aws ecr get-login-password --region (region명) | \
docker login --username AWS --password-stdin (ECR 레포지토리 주소)
```
**2) pull image**
```bash
docker pull (ECR 레포지토리 주소):10seconds-core
```
**3) run image**
```bash
docker run -it -d -p 3000:3000 (ECR 레포지토리 주소):10seconds-core
```
