using System.Threading.Tasks.Dataflow;
using System.Timers;
using Timer = System.Timers.Timer;

namespace FilesystemWatcherService
{
    public class TaskManager<TPayload>
    {
        private enum WorkType
        {
            Work,
            Clear
        }

        private class WorkItem
        {
            public WorkType Type { get; set; }

            public string Key { get; set; }

            public TPayload Payload { get; set; }
        }

        private class ContextQueue
        {
            private readonly ActionBlock<WorkItem> _queue;

            public DateTime LastAction { get; private set; }

            public bool IsEmpty => _queue.InputCount == 0;

            public ContextQueue(WorkCallback workCallback)
            {
                _queue = new ActionBlock<WorkItem>(
                    async workItem =>
                    {
                        LastAction = DateTime.UtcNow;

                        try
                        {
                            await workCallback(workItem.Key, workItem.Payload);
                        }
                        catch (Exception)
                        {
                            // TODO: Log the exception
                        }
                    },
                    new ExecutionDataflowBlockOptions
                    {
                        BoundedCapacity = DataflowBlockOptions.Unbounded,
                        MaxDegreeOfParallelism = 1,
                        SingleProducerConstrained = false,
                        CancellationToken = CancellationToken.None,
                    });
            }

            public bool Enqueue(WorkItem workItem)
            {
                return _queue.Post(workItem);
            }

            public Task CompleteAsync()
            {
                _queue.Complete();
                return _queue.Completion;
            }
        }

        public delegate Task WorkCallback(string key, TPayload payload);

        private readonly ActionBlock<WorkItem> _inboxActionBlock;
        private readonly Dictionary<string, ContextQueue> _queueMap = new();
        private readonly TimeSpan _inactivityTimeout = new(0, 15, 0);  // 15 minutes
        private readonly Timer _inactivityTimer;
        private bool _closed = false;

        public TaskManager(WorkCallback workCallback)
        {
            _inactivityTimer = new Timer
            {
                Interval = _inactivityTimeout.TotalMilliseconds,
                Enabled = true,
                AutoReset = true,
            };
            _inactivityTimer.Elapsed += ClearInactiveQueues;

            _inboxActionBlock = new ActionBlock<WorkItem>(
                async workItem =>
                {
                    string key = workItem.Key ?? "";

                    try
                    {
                        if (workItem.Type == WorkType.Clear && _queueMap.TryGetValue(key, out var contextQueue))
                        {
                            // Don't await if the context queue is not empty as it
                            // can block new items from being added to the inbox queue.
                            if (contextQueue.IsEmpty)
                            {
                                await contextQueue.CompleteAsync();
                                _queueMap.Remove(key);
                            }
                        }
                        else if (workItem.Type == WorkType.Work)
                        {
                            if (!_queueMap.TryGetValue(key, out contextQueue))
                            {
                                contextQueue = new ContextQueue(workCallback);
                                _queueMap[key] = contextQueue;
                            }
                            contextQueue.Enqueue(workItem);
                        }
                    }
                    catch (Exception e)
                    {
                        // Now catching all exceptions, because unhandled exceptions
                        // here will cause the ActionBlock to stop processing
                        
                    }
                },
                new ExecutionDataflowBlockOptions
                {
                    BoundedCapacity = DataflowBlockOptions.Unbounded,
                    MaxDegreeOfParallelism = 1,
                    SingleProducerConstrained = false,
                    CancellationToken = CancellationToken.None,
                });
        }

        public bool EnqueueWork(string key, TPayload payload)
        {
            if (_closed)
            {

                return false;
            }

            return _inboxActionBlock.Post(
                new WorkItem
                {
                    Type = WorkType.Work,
                    Key = key,
                    Payload = payload,
                });
        }

        public Task CompleteAsync()
        {
            _closed = true;
            return Task.WhenAll(
                _queueMap.Values.Select(q => q.CompleteAsync()));
        }

        private void ClearInactiveQueues(object sender, ElapsedEventArgs e)
        {
            var inactiveQueuePairs = _queueMap
                .Where(q => DateTime.UtcNow - q.Value.LastAction > _inactivityTimeout);
            foreach (var inactiveQueuePair in inactiveQueuePairs)
            {
                _inboxActionBlock.Post(new WorkItem
                {
                    Type = WorkType.Clear,
                    Key = inactiveQueuePair.Key,
                });
            }
        }
    }
}