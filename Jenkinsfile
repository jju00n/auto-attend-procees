pipeline {
    agent any

    // 파이프라인 전체 환경 변수 설정
    environment {
        AWS_REGION = 'ap-northeast-2'
        LAMBDA_FUNCTION_NAME = 'auto-attendance-bot'
        DEPLOY_PACKAGE_NAME = 'deployment_package.zip'
        PATH = "/usr/bin:$PATH"  // Python3 경로 추가
    }

    stages {

        stage('Checkout from GitHub') {
            steps {
                echo 'GitHub 저장소에서 최신 코드를 가져옵니다.'
                git branch: 'main', 
                    credentialsId: 'github-credentials', 
                    url: 'https://github.com/jju00n/auto-attend-procees.git'
            }
        }

        stage('Install Python Dependencies') {
            steps {
                echo 'Python3, pip 설치 및 venv 생성 확인'
                sh '''
                    # Python3 설치 (없을 경우)
                    if ! command -v python3 &> /dev/null; then
                        sudo dnf install -y python3 python3-devel python3-pip
                    fi

                    # 가상환경 생성
                    python3 -m venv venv

                    # venv 활성화 후 패키지 설치
                    source venv/bin/activate
                    python3 -m pip install --upgrade pip
                    python3 -m pip install -r requirements.txt

                    # 가상환경 확인
                    echo "Python 가상환경 위치:"
                    which python
                    python --version
                '''
            }
        }

        stage('Test Code Integrity') {
            steps {
                echo '단위 테스트 실행'
                sh '''
                    source venv/bin/activate
                    python3 -m unittest test_lambda_function.py
                '''
            }
        }

        stage('Package for Lambda') {
            steps {
                echo '배포용 ZIP 파일 생성'
                sh '''
                    source venv/bin/activate
                    mkdir -p package
                    python3 -m pip install --target ./package -r requirements.txt
                    cd package
                    zip -r ../${env.DEPLOY_PACKAGE_NAME} .
                    cd ..
                    zip -g ${env.DEPLOY_PACKAGE_NAME} lambda_function.py
                '''
            }
        }

        stage('Deploy to AWS Lambda') {
            steps {
                echo "AWS Lambda 함수 [${env.LAMBDA_FUNCTION_NAME}]에 배포 시작"
                withAWS(credentials: 'aws-credentials-for-lambda', region: env.AWS_REGION) {
                    lambdaUpdateFunction(
                        functionName: env.LAMBDA_FUNCTION_NAME,
                        zipFile: env.DEPLOY_PACKAGE_NAME
                    )
                }
                echo '배포 성공!'
            }
        }
    }

    post {
        always {
            echo '작업 공간 유지 (deleteDir 제거)'
            // deleteDir()는 제거하여 워크스페이스가 유지되도록 함
        }
    }
}