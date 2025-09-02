# 1. 베이스 이미지: 가장 안정적이고 표준적인 Java 11 버전으로 명시
FROM apache/spark:3.5.2-scala2.12-java11-python3-r-ubuntu

USER root

# --- ★★★ [해결 1] 주피터 랩 설치 추가 ★★★ ---
# curl과 함께 jupyterlab을 설치합니다.
# pyspark 버전을 명시하여 베이스 이미지와 버전을 정확히 일치시킵니다.
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && pip install --no-cache-dir jupyterlab pyspark==3.5.2 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/spark/jars

# 2. ARG 버전 정보는 그대로 사용
ARG ICEBERG_VERSION=1.9.2
ARG NESSIE_VERSION=0.104.9
ARG SPARK_KAFKA_VERSION=3.5.2
ARG TOKEN_PROVIDER_VERSION=3.5.2
ARG HADOOP_AWS_VERSION=3.4.0
ARG AWS_SDK_VERSION=1.12.749
ARG COMMONS_POOL2_VERSION=2.11.1

# --- ★★★ [해결 2] 다운로드 서버 변경 및 명령어 분리 ★★★ ---
# 다운로드 서버를 repo1.maven.org -> ftp.kaist.ac.kr/maven 으로 변경
# RUN 명령어를 분리하여 진행 상황을 보고 Docker 캐시를 활용합니다.
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/projectnessie/nessie-integrations/nessie-spark-extensions-3.5_2.12/${NESSIE_VERSION}/nessie-spark-extensions-3.5_2.12-${NESSIE_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_KAFKA_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_KAFKA_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/spark/spark-token-provider-kafka-0-10_2.12/${TOKEN_PROVIDER_VERSION}/spark-token-provider-kafka-0-10_2.12-${TOKEN_PROVIDER_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/kafka/kafka-clients/${SPARK_KAFKA_VERSION}/kafka-clients-${SPARK_KAFKA_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/commons/commons-pool2/${COMMONS_POOL2_VERSION}/commons-pool2-${COMMONS_POOL2_VERSION}.jar

# 모든 JAR을 자동으로 classpath에 포함
ENV SPARK_EXTRA_CLASSPATH=/opt/spark/jars/*

WORKDIR /opt/spark/work-dir
