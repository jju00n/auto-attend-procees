// Jenkinsfile
pipeline {
    agent any
    environment {
        AWS_REGION = 'ap-northeast-2'
        LAMBDA_FUNCTION_NAME = 'auto-attendance-bot'
        DEPLOY_PACKAGE_NAME = 'deployment_package.zip'
    }
    stages {
        stage('Checkout from GitHub') {
            steps {
                echo 'GitHub 저장소에서 최신 코드를 가져옵니다.'
                git branch: 'main', url: '[https://github.com/your-username/your-repo.git](https://github.com/your-username/your-repo.git)'
            }
        }
        stage('Test Code Integrity') {
            steps {
                echo '단위 테스트를 실행하여 코드의 무결성을 검증합니다.'
                sh '''
                    python3 -m venv venv
                    source venv/bin/activate
                    python3 -m pip install -r requirements.txt
                    python3 -m unittest test_lambda_function.py
                '''
            }
        }
        stage('Package for Lambda') {
            steps {
                echo '배포용 ZIP 압축 파일을 생성합니다.'
                sh '''
                    source venv/bin/activate
                    mkdir package
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
                echo "AWS Lambda 함수 [${env.LAMBDA_FUNCTION_NAME}]에 배포를 시작합니다."
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
            echo '작업 공간을 정리합니다.'
            deleteDir()
        }
    }
}