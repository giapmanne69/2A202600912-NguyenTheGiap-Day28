# Hướng Dẫn Nộp Bài - Lab #28: Full Platform Integration Sprint

## Yêu Cầu Nộp Bài

**Full AI infrastructure platform demo** - từ data ingestion đến model serving với full observability.

## Các Artifacts Cần Nộp

### 1. Source Code
- Folder `lab28/` hoàn chỉnh với tất cả files
- Tất cả integration scripts hoạt động
- Prefect flows đã deploy và schedule

### 2. Screenshots Demo
Chụp màn hình các bước:
- Prefect UI: http://localhost:4200 (flow đang chạy)
- API Gateway call: `curl http://localhost:8000/health`
- Grafana dashboard: http://localhost:3000

### 3. Kết Quả Smoke Tests
Chạy và chụp màn hình kết quả:
```bash
cd lab28
pytest smoke-tests/ -v
```
Kỳ vọng: 5/5 tests passing

### 4. Production Readiness Score
```bash
python scripts/production_readiness_check.py
```
Kỳ vọng: Score >80%

### 5. Documentation
- `README.md` giải thích cách:
  - Start platform: `docker compose up -d`
  - Deploy Prefect flows
  - Run smoke tests
  - Access dashboards (Grafana:3000, Prometheus:9090, Prefect:4200)

## Định Dạng Nộp Bài

Tạo Repo GitHub chứa:
```
lab28_submission_[student_id]
├── lab28/                    # Source code hoàn chỉnh
│   ├── docker-compose.yml
│   ├── prefect/flows/
│   ├── scripts/
│   ├── api-gateway/
│   └── monitoring/
├── screenshots/              # Screenshots demo
│   ├── prefect_ui.png
│   ├── api_gateway.png
│   └── grafana_dashboard.png
├── smoke_tests_results.png   # Screenshot kết quả pytest
├── production_readiness.png  # Screenshot readiness score
└── README.md                # Hướng dẫn setup
```

## Địa Điểm Nộp
Nộp link repo GitHub qua LMS

## Tiêu Chí Chấm Điểm

| Tiêu Chí | Trọng Số | Mô Tả |
|----------|----------|-------|
| Integration Completeness | 40% | Tất cả 10 integration points hoạt động, data flow end-to-end |
| Observability | 25% | Logs, metrics, traces hiển thị; alerts configured |
| Performance | 20% | Latency trong SLO; load tested; không có memory leaks |
| Architecture Quality | 15% | Clean separation, GitOps config, documented decisions |

## Các Vấn Đề Cần Tránh

- Config drift giữa các environments
- Thiếu error handling tại integration points
- Monitoring coverage không hoàn chỉnh
- Không có rollback strategy
- Demo không test trước khi nộp

## 5 Câu Hỏi Cần Trả Lời Khi Nộp

1. **Phân tích các trade-offs trong thiết kế kiến trúc AI platform của bạn. Bạn đã cân bằng giữa performance, reliability, và maintainability như thế nào?**
   - **Trade-off giữa Performance và Chi phí tài nguyên (Cost):** Để không quá tải tài nguyên máy local cấu hình thấp, chúng ta đã đưa mô hình LLM Qwen 7B lên chạy trên Kaggle GPU (miễn phí). Việc này tiết kiệm chi phí/tài nguyên phần cứng nhưng đánh đổi bằng độ trễ truyền dữ liệu mạng (network latency) thông qua ngrok/cloudflare tunnel (khoảng 8-10s cho mỗi request suy luận).
   - **Reliability (Độ tin cậy):** Decouple hoàn toàn quá trình ingestion và serving thông qua Kafka và Feast. Dữ liệu thô gửi đến được đệm ở Kafka, xử lý qua Prefect và lưu trữ trong Delta Lake trước khi đồng bộ sang Feast (Redis). Do đó, sự cố ở một thành phần không làm gián đoạn luồng dữ liệu của thành phần khác.
   - **Maintainability (Khả năng bảo trì):** Sử dụng các service tiêu chuẩn dưới dạng Container (Docker Compose) như Qdrant, Redis, Kafka giúp quản lý, nâng cấp dễ dàng và nhất quán giữa các môi trường chạy.

2. **Trong kiến trúc hybrid (Local + Kaggle), bạn xử lý ngắt kết nối giữa local và Kaggle như thế nào? Có cơ chế fallback không?**
   - **Xử lý ngắt kết nối:** Ngrok tunnel có thể bị ngắt kết nối do giới hạn phiên hoặc thay đổi IP ở phía Kaggle. 
   - **Cơ chế Fallback:**
     - *Phía Ingestion:* Prefect flow được tích hợp cơ chế retry tự động trong code task để xử lý lỗi mất kết nối tạm thời khi đẩy vector sang Qdrant.
     - *Phía Serving:* API Gateway được bọc trong các khối `try-except` với cài đặt `timeout` phù hợp (30 giây) để tránh bị treo vô hạn khi Kaggle bị sập. Để tối ưu hơn, có thể bổ sung một mô hình cục bộ siêu nhỏ (như Qwen-1.5B chạy CPU bằng Ollama trên local) làm fallback dự phòng khi không thể kết nối tới vLLM ngrok.

3. **Giải thích cách event-driven architecture với Kafka giúp decouple các components trong AI platform của bạn.**
   - **Decoupling:** Producer (`01_ingest_to_kafka.py`) chỉ gửi message trực tiếp vào topic `data.raw` của Kafka mà không cần biết khi nào hay làm thế nào dữ liệu đó được xử lý ở phía Delta Lake hay Qdrant.
   - **Khả năng chịu tải (Buffering):** Kafka hoạt động như một message queue đệm trung gian. Nếu dịch vụ tiêu thụ (Prefect flow runner) tạm thời bị offline để bảo trì, Kafka vẫn lưu trữ an toàn các message thô. Ngay khi Prefect runner khởi động lại, nó sẽ tự động tiêu thụ tiếp các message tồn đọng mà không làm mất mát bất kỳ dữ liệu nào của client gửi lên.

4. **Bạn đã implement observability như thế nào? Logs, metrics, và traces được thu thập và visualized ra sao?**
   - **Metrics:** API Gateway sử dụng middleware `prometheus_fastapi_instrumentator` để tự động thu thập các chỉ số hiệu năng (HTTP request count, latency, status code) và expose tại endpoint `/metrics`. Prometheus định kỳ pull dữ liệu này và Grafana trực quan hóa lên Dashboard.
   - **Traces:** Cấu hình biến môi trường kết nối trực tiếp đến LangSmith để ghi nhận toàn bộ trace và span của chuỗi hội thoại (từ tìm kiếm vector đến thời gian chạy suy luận LLM), giúp xác định các bottleneck một cách trực quan.
   - **Logs:** Toàn bộ log của các containers được quản lý tập trung qua Docker logs và cấu hình log quay vòng trong các thư mục dự án cục bộ của Prefect runner để phục vụ debug.

5. **Nếu một service trong stack (ví dụ: Qdrant hoặc Kafka) bị crash, hệ thống của bạn sẽ xử lý như thế nào? Có graceful degradation không?**
   - **Kafka crash:** Dữ liệu mới tạm thời không thể nạp vào Delta Lake, nhưng hệ thống vẫn thực hiện suy luận RAG bình thường nhờ dữ liệu tĩnh hiện có trong Vector Store (Qdrant) và Feature Store (Redis).
   - **Qdrant (Vector Store) crash:** API Gateway sẽ bắt lỗi kết nối Vector Search một cách êm ái (graceful degradation), bỏ qua context tìm kiếm ngữ cảnh, và trực tiếp gửi câu hỏi thô tới LLM. User vẫn nhận được phản hồi từ tri thức gốc của LLM thay vì gặp lỗi hệ thống 500.
   - **Feast (Redis) crash:** API Gateway có thể fallback đọc trực tiếp các feature tĩnh tương ứng từ file Parquet trong Delta Lake (hoặc dùng cache cục bộ trong bộ nhớ tạm) để duy trì hoạt động phục vụ suy luận.

## Câu Hỏi Thêm?
Liên hệ giảng viên qua LMS hoặc office hours.
