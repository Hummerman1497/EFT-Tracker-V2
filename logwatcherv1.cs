using System;
using System.IO;
using System.Threading;
using System.Reflection;
using System.Collections.Generic;
using System.Linq;

namespace EFTLogMonitor
{
    class Program
    {
        static bool statisticsFound = false;
        static string logFolderPath = null;
        static bool isRunning = true;
        static string currentNetLogPath = null;
        static string currentBackendLogPath = null;
        static readonly object netLogLock = new object();
        static readonly object backendLogLock = new object();
        static Dictionary<string, Thread> activeMonitorThreads = new Dictionary<string, Thread>();

        static void Main(string[] args)
        {
            Console.WriteLine("EFT LogWatcher started");

            // Pfad aus Kommandozeilenargumenten lesen
            if (args.Length > 0 && !string.IsNullOrEmpty(args[0]))
            {
                logFolderPath = args[0];
                Console.WriteLine($"Log folder path from command line: {logFolderPath}");
            }
            else
            {
                // Try to get the path from the configuration file
                try
                {
                    // Get the directory where the executable is located
                    string exeDirectory = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
                    if (exeDirectory == null)
                    {
                        Console.WriteLine("Warning: Could not determine executable directory");
                        exeDirectory = AppDomain.CurrentDomain.BaseDirectory;
                        Console.WriteLine($"Using base directory instead: {exeDirectory}");
                    }

                    string configFilePath = Path.Combine(exeDirectory, "eft_logs_path.txt");
                    Console.WriteLine($"Looking for config file at: {configFilePath}");

                    if (File.Exists(configFilePath))
                    {
                        logFolderPath = File.ReadAllText(configFilePath).Trim();
                        Console.WriteLine($"Log folder path from config file: {logFolderPath}");
                    }
                    else
                    {
                        Console.WriteLine($"Config file not found at: {configFilePath}");

                        // Fallback: Try parent directory
                        string parentDir = Directory.GetParent(exeDirectory)?.FullName;
                        if (!string.IsNullOrEmpty(parentDir))
                        {
                            string parentConfigPath = Path.Combine(parentDir, "eft_logs_path.txt");
                            Console.WriteLine($"Trying parent directory: {parentConfigPath}");

                            if (File.Exists(parentConfigPath))
                            {
                                logFolderPath = File.ReadAllText(parentConfigPath).Trim();
                                Console.WriteLine($"Log folder path from parent config file: {logFolderPath}");
                            }
                        }

                        // Another fallback: Try to auto-detect common EFT paths
                        if (string.IsNullOrEmpty(logFolderPath))
                        {
                            string[] commonPaths = {
                                @"C:\Battlestate Games\EFT\Logs",
                                @"D:\Battlestate Games\EFT\Logs",
                                @"E:\Battlestate Games\EFT\Logs"
                                };

                            foreach (string path in commonPaths)
                            {
                                if (Directory.Exists(path))
                                {
                                    logFolderPath = path;
                                    Console.WriteLine($"Auto-detected EFT logs path: {logFolderPath}");
                                    break;
                                }
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error reading config file: {ex.Message}");
                    Console.WriteLine($"Stack trace: {ex.StackTrace}");
                }
            }

            if (string.IsNullOrEmpty(logFolderPath) || !Directory.Exists(logFolderPath))
            {
                Console.WriteLine("ERROR_INVALID_PATH");
                return;
            }

            Console.WriteLine($"MONITORING_STARTED:{logFolderPath}");
            StartMonitoring();

            // Periodically check for new log files
            Thread periodicCheckThread = new Thread(PeriodicCheckForNewLogs);
            periodicCheckThread.IsBackground = true;
            periodicCheckThread.Start();

            Thread inputThread = new Thread(ReadConsoleInput);
            inputThread.IsBackground = true;
            inputThread.Start();

            // Warte auf Beendigung
            while (isRunning)
            {
                Thread.Sleep(1000);
            }
        }

        static void ReadConsoleInput()
        {
            while (isRunning)
            {
                string input = Console.ReadLine();
                if (input == "RESET_FLAG")
                {
                    statisticsFound = false;
                    Console.WriteLine("STATISTICS_FLAG_RESET");
                }
                else if (input == "EXIT" || input == "QUIT")
                {
                    isRunning = false;
                    Console.WriteLine("Shutting down...");
                }
                else if (input == "STATUS")
                {
                    PrintStatus();
                }
                else if (input == "REFRESH")
                {
                    Console.WriteLine("Manually refreshing log files...");
                    CheckForNewLogFiles();
                }
            }
        }

        static void PrintStatus()
        {
            Console.WriteLine("==== LogWatcher Status ====");
            Console.WriteLine($"Log Folder: {logFolderPath}");
            Console.WriteLine($"Statistics Flag: {statisticsFound}");
            Console.WriteLine($"Current NetLog: {currentNetLogPath ?? "None"}");
            Console.WriteLine($"Current BackendLog: {currentBackendLogPath ?? "None"}");
            Console.WriteLine($"Active Monitor Threads: {activeMonitorThreads.Count}");
            Console.WriteLine("=========================");
        }

        static void StartMonitoring()
        {
            try
            {
                Console.WriteLine($"Starting monitoring of log folder: {logFolderPath}");

                // Watcher für network-connection.log
                var watcherNet = new FileSystemWatcher
                {
                    Path = logFolderPath,
                    Filter = "*.*", // Überwache alle Dateien
                    NotifyFilter = NotifyFilters.FileName | NotifyFilters.DirectoryName
                };
                watcherNet.IncludeSubdirectories = true;

                watcherNet.Created += (sender, e) =>
                {
                    if (e.Name.Contains("network-connection") && e.Name.EndsWith(".log"))
                    {
                        ProcessNewNetworkLog(e.FullPath);
                    }
                };

                watcherNet.EnableRaisingEvents = true;
                Console.WriteLine("Started looking for net.log");

                // Watcher für backend.log
                var watcherTrac = new FileSystemWatcher
                {
                    Path = logFolderPath,
                    Filter = "*.*",
                    NotifyFilter = NotifyFilters.FileName | NotifyFilters.DirectoryName
                };
                watcherTrac.IncludeSubdirectories = true;

                watcherTrac.Created += (sender, e) =>
                {
                    if (e.Name.Contains("backend") && e.Name.EndsWith(".log"))
                    {
                        ProcessNewBackendLog(e.FullPath);
                    }
                };

                watcherTrac.EnableRaisingEvents = true;
                Console.WriteLine("Started looking for backend.log");

                // Suche auch nach bereits vorhandenen Dateien
                SearchExistingLogFiles(logFolderPath);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"ERROR_MONITORING: {ex.Message}");
            }
        }

        static void PeriodicCheckForNewLogs()
        {
            while (isRunning)
            {
                // Check every minute for new logs
                Thread.Sleep(60000);
                CheckForNewLogFiles();
            }
        }

        static void CheckForNewLogFiles()
        {
            try
            {
                // Check if there are newer log files that we should be monitoring
                SearchExistingLogFiles(logFolderPath, true);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error in periodic check: {ex.Message}");
            }
        }

        static void ProcessNewNetworkLog(string logFilePath)
        {
            lock (netLogLock)
            {
                DateTime newFileTime = File.GetCreationTime(logFilePath);

                // If we don't have a current log or this one is newer
                if (currentNetLogPath == null ||
                    (File.Exists(currentNetLogPath) && newFileTime > File.GetCreationTime(currentNetLogPath)))
                {
                    Console.WriteLine($"Found new/newer net.log: {logFilePath}");

                    // Kill old monitoring thread if exists
                    if (currentNetLogPath != null && activeMonitorThreads.ContainsKey(currentNetLogPath))
                    {
                        try
                        {
                            activeMonitorThreads[currentNetLogPath].Abort();
                            activeMonitorThreads.Remove(currentNetLogPath);
                        }
                        catch { /* Ignore thread abort errors */ }
                    }

                    currentNetLogPath = logFilePath;
                    MonitorNetLogFile(logFilePath);
                }
            }
        }

        static void ProcessNewBackendLog(string logFilePath)
        {
            lock (backendLogLock)
            {
                DateTime newFileTime = File.GetCreationTime(logFilePath);

                // If we don't have a current log or this one is newer
                if (currentBackendLogPath == null ||
                    (File.Exists(currentBackendLogPath) && newFileTime > File.GetCreationTime(currentBackendLogPath)))
                {
                    Console.WriteLine($"Found new/newer backend.log: {logFilePath}");

                    // Kill old monitoring thread if exists
                    if (currentBackendLogPath != null && activeMonitorThreads.ContainsKey(currentBackendLogPath))
                    {
                        try
                        {
                            activeMonitorThreads[currentBackendLogPath].Abort();
                            activeMonitorThreads.Remove(currentBackendLogPath);
                        }
                        catch { /* Ignore thread abort errors */ }
                    }

                    currentBackendLogPath = logFilePath;
                    StartMonitoringTracesLog(logFilePath);
                }
            }
        }

        static void SearchExistingLogFiles(string logFolderPath, bool onlyCheckNewer = false)
        {
            try
            {
                // Suche nach bestehenden network-connection.log Dateien
                var networkLogFiles = Directory.GetFiles(logFolderPath, "*network-connection*.log", SearchOption.AllDirectories);
                if (networkLogFiles.Length > 0)
                {
                    // Sortiere nach Erstellungsdatum, neueste zuerst
                    Array.Sort(networkLogFiles, (a, b) => File.GetCreationTime(b).CompareTo(File.GetCreationTime(a)));
                    var latestNetLog = networkLogFiles[0];

                    if (!onlyCheckNewer ||
                        currentNetLogPath == null ||
                        File.GetCreationTime(latestNetLog) > File.GetCreationTime(currentNetLogPath))
                    {
                        ProcessNewNetworkLog(latestNetLog);
                    }
                }

                // Suche nach bestehenden backend.log Dateien
                var backendLogFiles = Directory.GetFiles(logFolderPath, "*backend*.log", SearchOption.AllDirectories);
                if (backendLogFiles.Length > 0)
                {
                    // Sortiere nach Erstellungsdatum, neueste zuerst
                    Array.Sort(backendLogFiles, (a, b) => File.GetCreationTime(b).CompareTo(File.GetCreationTime(a)));
                    var latestBackendLog = backendLogFiles[0];

                    if (!onlyCheckNewer ||
                        currentBackendLogPath == null ||
                        File.GetCreationTime(latestBackendLog) > File.GetCreationTime(currentBackendLogPath))
                    {
                        ProcessNewBackendLog(latestBackendLog);
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error searching existing log files: {ex.Message}");
            }
        }

        static void MonitorNetLogFile(string logFilePath)
        {
            var thread = new Thread(() =>
            {
                try
                {
                    Console.WriteLine($"Monitoring net.log: {logFilePath}");

                    using (var stream = new FileStream(logFilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    using (var reader = new StreamReader(stream))
                    {
                        string line;

                        // Springe zum Ende der Datei, um nur neue Einträge zu überwachen
                        stream.Seek(0, SeekOrigin.End);

                        while (isRunning && currentNetLogPath == logFilePath)
                        {
                            try
                            {
                                if ((line = reader.ReadLine()) != null)
                                {
                                    if (line.Contains("Statistics") && !statisticsFound)
                                    {
                                        Console.WriteLine("Statistics found!");
                                        statisticsFound = true;
                                        // Direkter Trigger über Konsole
                                        Console.WriteLine("TRIGGER_NETLOG_STATISTICS");
                                    }
                                }
                                else
                                {
                                    // Check if the file still exists - it might have been deleted
                                    if (!File.Exists(logFilePath))
                                    {
                                        Console.WriteLine($"Net.log file no longer exists: {logFilePath}");
                                        break;
                                    }
                                    Thread.Sleep(100);
                                }
                            }
                            catch (IOException ioEx)
                            {
                                // Handle file access errors (e.g., file was deleted)
                                Console.WriteLine($"IO error with net.log: {ioEx.Message}");
                                break;
                            }
                        }
                    }
                }
                catch (ThreadAbortException)
                {
                    // Thread was aborted, clean shutdown
                    Console.WriteLine($"Net.log monitor thread for {logFilePath} was stopped");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"ERROR_NETLOG: {ex.Message}");
                }
                finally
                {
                    lock (netLogLock)
                    {
                        if (activeMonitorThreads.ContainsKey(logFilePath))
                        {
                            activeMonitorThreads.Remove(logFilePath);
                        }

                        // If this was the current log and it failed, trigger a refresh
                        if (currentNetLogPath == logFilePath)
                        {
                            Console.WriteLine("Current net.log monitor failed, checking for new logs...");
                            CheckForNewLogFiles();
                        }
                    }
                }
            });

            thread.IsBackground = true;
            thread.Start();

            lock (netLogLock)
            {
                activeMonitorThreads[logFilePath] = thread;
            }
        }

        static void StartMonitoringTracesLog(string logFilePath)
        {
            var thread = new Thread(() =>
            {
                try
                {
                    Console.WriteLine($"Monitoring backend.log: {logFilePath}");

                    using (var stream = new FileStream(logFilePath, FileMode.Open, FileAccess.Read, FileShare.ReadWrite))
                    using (var reader = new StreamReader(stream))
                    {
                        string line;

                        // Springe zum Ende der Datei, um nur neue Einträge zu überwachen
                        stream.Seek(0, SeekOrigin.End);

                        while (isRunning && currentBackendLogPath == logFilePath)
                        {
                            try
                            {
                                if ((line = reader.ReadLine()) != null)
                                {
                                    if (line.Contains("<--- Response HTTPS") && statisticsFound)
                                    {
                                        Console.WriteLine($"Trigger: {line}");

                                        int n = 0;
                                        bool newLineDetected = false;

                                        while (n < 5 && isRunning)
                                        {
                                            Thread.Sleep(50);
                                            if (reader.ReadLine() != null)
                                            {
                                                newLineDetected = true;
                                                break;
                                            }
                                            n++;
                                        }

                                        if (!newLineDetected && isRunning)
                                        {
                                            Console.WriteLine("Trigger! Backend.log trigger detected.");
                                            // Direkter Trigger über Konsole
                                            Console.WriteLine("TRIGGER_SCREENSHOT");
                                            statisticsFound = false;
                                        }
                                    }
                                }
                                else
                                {
                                    // Check if the file still exists - it might have been deleted
                                    if (!File.Exists(logFilePath))
                                    {
                                        Console.WriteLine($"Backend.log file no longer exists: {logFilePath}");
                                        break;
                                    }
                                    Thread.Sleep(50);
                                }
                            }
                            catch (IOException ioEx)
                            {
                                // Handle file access errors (e.g., file was deleted)
                                Console.WriteLine($"IO error with backend.log: {ioEx.Message}");
                                break;
                            }
                        }
                    }
                }
                catch (ThreadAbortException)
                {
                    // Thread was aborted, clean shutdown
                    Console.WriteLine($"Backend.log monitor thread for {logFilePath} was stopped");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"ERROR_BACKEND: {ex.Message}");
                }
                finally
                {
                    lock (backendLogLock)
                    {
                        if (activeMonitorThreads.ContainsKey(logFilePath))
                        {
                            activeMonitorThreads.Remove(logFilePath);
                        }

                        // If this was the current log and it failed, trigger a refresh
                        if (currentBackendLogPath == logFilePath)
                        {
                            Console.WriteLine("Current backend.log monitor failed, checking for new logs...");
                            CheckForNewLogFiles();
                        }
                    }
                }
            });

            thread.IsBackground = true;
            thread.Start();

            lock (backendLogLock)
            {
                activeMonitorThreads[logFilePath] = thread;
            }
        }

        // Hilfsmethode zum Zurücksetzen des statisticsFound-Flags von außen
        public static void ResetStatisticsFlag()
        {
            statisticsFound = false;
            Console.WriteLine("STATISTICS_FLAG_RESET");
        }
    }
}
