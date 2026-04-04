using System;
using System.Collections.Generic;
using System.Net.Http;
using System.Text;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Newtonsoft.Json.Serialization;

namespace UpmClient.Services
{
    // --- 데이터 모델 정의 (서버 JSON 명세서와 일치) ---
    public class ProcessInfo
    {
        public int ProcessId { get; set; }
        public string ProcessName { get; set; }
        public long MemoryWorkingSetBytes { get; set; }
        public bool IsSystemCritical { get; set; }
    }

    public class TelemetryData
    {
        public string MachineId { get; set; }
        public double CpuUsagePercent { get; set; }
        public double RamUsagePercent { get; set; }
        public double GpuTemperatureCelsius { get; set; }
        public DateTime Timestamp { get; set; }
        public List<ProcessInfo> TopProcesses { get; set; }
    }

    public class UpmApiService
    {
        private readonly HttpClient _httpClient;
        private readonly string _baseUrl = "http://127.0.0.1:8000/api/v1"; // FastAPI 서버 주소

        public UpmApiService()
        {
            _httpClient = new HttpClient();
        }

        // 📊 2.1. 텔레메트리 전송 (Desktop -> Server)
        public async Task<bool> SendMetricsAsync(TelemetryData data)
        {
            try
            {
                // C# 객체를 camelCase JSON으로 변환
                var settings = new JsonSerializerSettings { ContractResolver = new CamelCasePropertyNamesContractResolver() };
                string json = JsonConvert.SerializeObject(data, settings);
                var content = new StringContent(json, Encoding.UTF8, "application/json");

                var response = await _httpClient.PostAsync($"{_baseUrl}/metrics", content);
                return response.IsSuccessStatusCode;
            }
            catch (Exception ex)
            {
                Console.WriteLine($"데이터 전송 오류: {ex.Message}");
                return false;
            }
        }

        // 🛡️ 2.2. 최적화 룰셋 수신 (Server -> Desktop)
        public async Task<string> GetOptimizationRulesAsync()
        {
            try
            {
                var response = await _httpClient.GetStringAsync($"{_baseUrl}/optimization/rules");
                return response; // JSON 문자열 반환 (이후 파싱하여 로직에 활용)
            }
            catch (Exception ex)
            {
                Console.WriteLine($"룰셋 수신 오류: {ex.Message}");
                return null;
            }
        }
    }
}