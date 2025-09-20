pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-northeast-2'
        LAMBDA_FUNCTION_NAME = 'auto-attendance-bot'
        DEPLOY_PACKAGE_NAME = 'deployment_package.zip'
        PATH = "/usr/bin:$PATH"  // 참고용, 절대 경로 사용으로 안전
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
                echo 'Python3 설치 확인 및 venv 생성'
                sh '''
                    # Python3 설치 확인 (없으면 설치)
                    if ! command -v /usr/bin/python3 &> /dev/null; then
                        sudo dnf install -y python3 python3-devel python3-pip
                    fi

                    # 이전 venv 삭제
                    rm -rf venv

                    # 절대 경로로 venv 생성
                    /usr/bin/python3 -m venv venv

                    # venv 활성화 및 패키지 설치
                    source venv/bin/activate
                    /usr/bin/python3 -m pip install --upgrade pip
                    /usr/bin/python3 -m pip install -r requirements.txt

                    # venv 확인
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
                    /usr/bin/python3 -m unittest test_lambda_function.py
                '''
            }
        }

        stage('Package for Lambda') {
            steps {
                echo '배포용 ZIP 파일 생성'
                sh '''
                    source venv/bin/activate
                    mkdir -p package
                    /usr/bin/python3 -m pip install --target ./package -r requirements.txt
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
            // deleteDir() 제거하여 워크스페이스 유지
        }
    }
}