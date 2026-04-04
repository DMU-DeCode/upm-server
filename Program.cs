using System;
using System.Collections.Generic;
using System.Management; // 실제 하드웨어 정보를 읽기 위한 필수 네임스페이스
using System.Threading.Tasks;
using UpmClient.Services;

class Program
{
    static async Task Main(string[] args)
    {
        Console.WriteLine("🚀 UPM 실제 하드웨어 수집 에이전트 시작...");
        
        var apiService = new UpmApiService();
        string myMachineId = Environment.MachineName; // 내 PC의 실제 이름 가져오기

        // 1초마다 반복해서 서버로 데이터를 쏘는 무한 루프
        while (true)
        {
            try
            {
                // 1. 실제 CPU 사용량 읽기 (WMI)
                double cpuUsage = GetRealCpuUsage();
                
                // 2. 실제 RAM 사용량 읽기 (WMI)
                double ramUsage = GetRealRamUsage();

                // 3. 서버로 보낼 JSON 데이터 패키징
                var realData = new TelemetryData
                {
                    MachineId = $"UPM_{myMachineId}", // 예: UPM_DESKTOP-ABC
                    CpuUsagePercent = cpuUsage,
                    RamUsagePercent = ramUsage,
                    GpuTemperatureCelsius = 50.0, // GPU는 외부 라이브러리가 필요하므로 일단 고정값
                    Timestamp = DateTime.UtcNow,
                    TopProcesses = new List<ProcessInfo>() // 프로세스 목록은 다음 단계에서 추가
                };

                // 4. FastAPI 서버로 전송
                Console.Write($"[{DateTime.Now:HH:mm:ss}] CPU: {cpuUsage:F1}% | RAM: {ramUsage:F1}% ➔ ");
                bool success = await apiService.SendMetricsAsync(realData);

                if (success) {
                    Console.ForegroundColor = ConsoleColor.Green;
                    Console.WriteLine("서버 전송 성공!");
                    Console.ResetColor();
                } else {
                    Console.ForegroundColor = ConsoleColor.Red;
                    Console.WriteLine("서버 전송 실패...");
                    Console.ResetColor();
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"에러 발생: {ex.Message}");
            }

            // 명세서 규격에 맞게 1초(1000ms) 대기 후 다시 수집
            await Task.Delay(1000);
        }
    }

    // 🔍 윈도우 OS에서 진짜 CPU 사용량을 캐오는 함수 
    static double GetRealCpuUsage()
    {
        try {
            using var searcher = new ManagementObjectSearcher("select LoadPercentage from Win32_Processor");
            foreach (var obj in searcher.Get()) {
                return Convert.ToDouble(obj["LoadPercentage"]);
            }
        } catch { }
        return 0.0;
    }

    // 🔍 윈도우 OS에서 진짜 RAM 사용량을 캐오는 함수 
    static double GetRealRamUsage()
    {
        try {
            using var searcher = new ManagementObjectSearcher("select FreePhysicalMemory, TotalVisibleMemorySize from Win32_OperatingSystem");
            foreach (var obj in searcher.Get()) {
                double total = Convert.ToDouble(obj["TotalVisibleMemorySize"]);
                double free = Convert.ToDouble(obj["FreePhysicalMemory"]);
                // (전체 - 남은공간) / 전체 * 100 = 현재 사용률(%)
                return Math.Round(((total - free) / total) * 100, 1);
            }
        } catch { }
        return 0.0;
    }
}