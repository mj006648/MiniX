# 1. 베이스 이미지: Spark 3.5.2
FROM apache/spark:3.5.2-scala2.12-java11-python3-r-ubuntu

USER root

# --- [수정] AI 에이전트 및 주피터 랩 필수 라이브러리 설치 ---
RUN apt-get update && apt-get install -y --no-install-recommends curl \
 && pip install --no-cache-dir \
    jupyterlab \
    pyspark==3.5.2 \
    pymilvus==2.4.4 \
    requests==2.31.0 \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/spark/jars

# 2. JAR 버전 정보
ARG ICEBERG_VERSION=1.9.2
ARG NESSIE_VERSION=0.104.9
ARG SPARK_KAFKA_VERSION=3.5.2
ARG TOKEN_PROVIDER_VERSION=3.5.2
ARG HADOOP_AWS_VERSION=3.4.0
ARG AWS_SDK_VERSION=1.12.749
ARG COMMONS_POOL2_VERSION=2.11.1

# 3. JAR 다운로드 (KAIST 미러 서버 사용)
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/iceberg/iceberg-spark-runtime-3.5_2.12/${ICEBERG_VERSION}/iceberg-spark-runtime-3.5_2.12-${ICEBERG_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/projectnessie/nessie-integrations/nessie-spark-extensions-3.5_2.12/${NESSIE_VERSION}/nessie-spark-extensions-3.5_2.12-${NESSIE_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/hadoop/hadoop-aws/${HADOOP_AWS_VERSION}/hadoop-aws-${HADOOP_AWS_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/com/amazonaws/aws-java-sdk-bundle/${AWS_SDK_VERSION}/aws-java-sdk-bundle-${AWS_SDK_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/spark/spark-sql-kafka-0-10_2.12/${SPARK_KAFKA_VERSION}/spark-sql-kafka-0-10_2.12-${SPARK_KAFKA_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/spark/spark-token-provider-kafka-0-10_2.12/${TOKEN_PROVIDER_VERSION}/spark-token-provider-kafka-0-10_2.12-${TOKEN_PROVIDER_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/kafka/kafka-clients/${SPARK_KAFKA_VERSION}/kafka-clients-${SPARK_KAFKA_VERSION}.jar
RUN curl -LO https://ftp.kaist.ac.kr/maven/org/apache/commons/commons-pool2/${COMMONS_POOL2_VERSION}/commons-pool2-${COMMONS_POOL2_VERSION}.jar

# 모든 JAR을 classpath에 포함
ENV SPARK_EXTRA_CLASSPATH=/opt/spark/jars/*

WORKDIR /opt/spark/work-dir
USER spark
