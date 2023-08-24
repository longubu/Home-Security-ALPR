using Microsoft.Extensions.FileSystemGlobbing;
using System.Diagnostics;
using System.Threading.Tasks.Dataflow;

namespace FilesystemWatcherService
{
    public class WorkPayload
    {
        public string FilePath { get; set; }
    }

    public class FileWatcherService : IHostedService
    {

        private readonly ILogger<FileWatcherService> _logger;
        private readonly FileSystemWatcher _watcher;
        private readonly TaskManager<WorkPayload> _taskManager;
        private readonly string PythonPath;
        private readonly string ScriptPath;
        private readonly string PathToWatch;
        private const string VideoFilter = "*.mp4";
        private const int DELAY_TIMER = 60000;
        
        public FileWatcherService(ILogger<FileWatcherService> logger)
        {
            _logger = logger;

            PythonPath = @"C:\Users\Lbot3000\.pyenv\pyenv-win\versions\3.9.2\python.exe";

            // Replace this with the path to your Python script
            ScriptPath = @"C:\Users\Lbot3000\Documents\dev\github\homesecurity_alpr\python\process_video.py";

            PathToWatch = @"C:\HomeSecurity_ALPR\ftp";

            _watcher = new FileSystemWatcher(PathToWatch);

            _watcher.NotifyFilter = NotifyFilters.Attributes
                     | NotifyFilters.CreationTime
                     | NotifyFilters.DirectoryName
                     | NotifyFilters.FileName
                     | NotifyFilters.LastAccess
                     | NotifyFilters.LastWrite
                     | NotifyFilters.Security
                     | NotifyFilters.Size;

            _watcher.Created += OnCreated;
            _watcher.Filter = VideoFilter;
            _watcher.IncludeSubdirectories = true;
            _watcher.EnableRaisingEvents = true;

            _taskManager = new TaskManager<WorkPayload>(ProcessActionBlock);

        }

        public Task StartAsync(CancellationToken cancellationToken)
        {

            _logger.LogInformation($"Starting FileWatcher @:{PathToWatch}, Filter: {VideoFilter}");

            return Task.CompletedTask;
        }

        public Task StopAsync(CancellationToken cancellationToken)
        {
            _watcher.Dispose();
            return Task.CompletedTask;
        }


        private void OnCreated(object sender, FileSystemEventArgs e)
        {
            string path = e.FullPath;

            _logger.LogInformation($"Video Queued: {e.FullPath} @ {DateTime.Now.ToShortTimeString()}");

            Timer timer = new Timer(DelayTimerCallback, path, DELAY_TIMER, Timeout.Infinite);

        }

        private  void DelayTimerCallback(object? state)
        {
            string path = state as string;

            if (string.IsNullOrEmpty(path))
            {
                _logger.LogWarning("Unable to get Path from callback state");
                return;
            }
            //ExecutePython(path);

            _taskManager.EnqueueWork(path, new WorkPayload()
            {
                FilePath = path
            });
        }

        private Task ProcessActionBlock(string key, WorkPayload payload)
        {
            ExecutePython(payload.FilePath);
            return Task.CompletedTask;
        }

        private void ExecutePython(string videoPath)
        {


            string fullPythonPathWithArgs = $"{ScriptPath} {videoPath}";
            // Create a ProcessStartInfo object to configure the Python process
            ProcessStartInfo psi = new ProcessStartInfo
            {
                FileName = PythonPath,
                Arguments = fullPythonPathWithArgs,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                UseShellExecute = false,
                CreateNoWindow = false
            };

            // Create the Python process
            _logger.LogInformation($"Starting Python Script with Params: {fullPythonPathWithArgs}");

            using (Process pythonProcess = new Process())
            {
                pythonProcess.StartInfo = psi;

                // Event handlers to capture output/error messages
                pythonProcess.OutputDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e?.Data))
                    {
                        _logger.LogInformation($"Python Output: {e.Data}");
                    }
                };
                pythonProcess.ErrorDataReceived += (sender, e) =>
                {
                    if (!string.IsNullOrEmpty(e?.Data))
                    {
                        _logger.LogError("Python Output Error: " + e.Data);
                    }
                };

                // Start the Python process
                pythonProcess.Start();

                // Begin asynchronous reading of the output/error streams
                pythonProcess.BeginOutputReadLine();
                pythonProcess.BeginErrorReadLine();

                // Wait for the process to finish
                pythonProcess.WaitForExit();

                // Get the exit code
                int exitCode = pythonProcess.ExitCode;
                _logger.LogInformation($"Python script exited with code {exitCode}");

                if (exitCode == 0)
                {
                    try
                    {
                        _logger.LogInformation($"Deleting File: {videoPath}");
                        File.Delete(videoPath);
                    }
                    catch (Exception) { }
                    
                }
            }
        }
    }
}

