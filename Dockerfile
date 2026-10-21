# Self-contained submission image.
#
# Build:
#   docker build -t scan-insertion-agent .
# Run:
#   docker run --rm \
#     -v /path/to/input:/work/input \
#     -v /path/to/output:/work/output \
#     -e DASHSCOPE_API_KEY \
#     scan-insertion-agent -input /work/input/hidden_case_1 \
#                          -output /work/output/hidden_case_1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/submission

WORKDIR /submission

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY agent_system ./
COPY src ./src
COPY configs ./configs
COPY schemas ./schemas
COPY docs ./docs
COPY manual ./manual

RUN chmod +x /submission/agent_system

ENTRYPOINT ["/submission/agent_system"]
