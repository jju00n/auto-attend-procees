pipeline {
    agent any

    environment {
        AWS_REGION = 'ap-northeast-2'
        LAMBDA_FUNCTION_NAME = 'auto-attendance-bot'
        DEPLOY_PACKAGE_NAME = 'deployment_package.zip'
        PATH = "/usr/bin:$PATH"
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
                    if ! command -v /usr/bin/python3 &> /dev/null; then
                        sudo dnf install -y python3 python3-devel python3-pip
                    fi

                    rm -rf venv
                    /usr/bin/python3 -m venv venv
                    source venv/bin/activate
                    /usr/bin/python3 -m pip install --upgrade pip
                    /usr/bin/python3 -m pip install -r requirements.txt

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
                    zip -r ../$DEPLOY_PACKAGE_NAME .
                    cd ..
                    zip -g $DEPLOY_PACKAGE_NAME lambda_function.py

                    if [ ! -f "$DEPLOY_PACKAGE_NAME" ]; then
                        echo "ERROR: $DEPLOY_PACKAGE_NAME 파일이 존재하지 않습니다!"
                        exit 1
                    fi
                '''
            }
        }

        stage('Check Lambda Function') {
            steps {
                echo "Lambda 함수 [${env.LAMBDA_FUNCTION_NAME}] 존재 여부 확인"
                withAWS(credentials: 'aws-credentials-for-lambda', region: "${AWS_REGION}") {
                    sh '''
                        aws lambda get-function --function-name ${LAMBDA_FUNCTION_NAME} || {
                            echo "ERROR: Lambda 함수 ${LAMBDA_FUNCTION_NAME} 가 존재하지 않거나 접근 불가"
                            exit 1
                        }
                    '''
                }
            }
        }

        stage('Deploy to AWS Lambda') {
            steps {
                echo "AWS Lambda 함수 [${env.LAMBDA_FUNCTION_NAME}]에 배포 시작"
                withAWS(credentials: 'aws-credentials-for-lambda', region: "${AWS_REGION}") {
                    sh '''
                        aws lambda update-function-code \
                            --function-name ${LAMBDA_FUNCTION_NAME} \
                            --zip-file fileb://${DEPLOY_PACKAGE_NAME} || {
                                echo "ERROR: Lambda 업로드 실패"
                                exit 1
                            }
                        echo '배포 성공!'
                    '''
                }
            }
        }
    }

    post {
        always {
            echo '작업 공간 유지 (deleteDir 제거)'
        }
        failure {
            echo '배포 실패! 로그를 확인하세요.'
        }
        success {
            echo '전체 파이프라인 완료!'
        }
    }
}