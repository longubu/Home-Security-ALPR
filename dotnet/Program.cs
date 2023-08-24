using FilesystemWatcherService;

var host = Host.CreateDefaultBuilder(args)
    .ConfigureServices(services => { services.AddHostedService<FileWatcherService>(); })
    .Build(); // Build the host, as per configurations.

await host.RunAsync();