# Benchmark computer and software environment

The definitive balanced and challenge experiments ran on the same Dell
OptiPlex SFF Plus 7010 under 64-bit Windows 11. Windows system information
and PowerShell reported the following hardware:

| Component | Specification |
| --- | --- |
| Processor | Intel Core i7-13700 |
| CPU topology | 16 physical cores; 24 logical processors |
| Memory | 32 GB installed (31.7 GB usable) |
| Storage | Two KIOXIA BG6 1024 GB NVMe SSDs; the C: volume is on disk 0 |

The original environment records report Windows build
`Windows-11-10.0.26200-SP0` and the CPU identifier
`Intel64 Family 6 Model 183 Stepping 1, GenuineIntel`. The balanced experiments
used 64-bit Anaconda Python 3.12.15; the challenge experiments used 64-bit
Anaconda Python 3.12.16. Each timed run had a wall-time limit of 600 seconds
and a process-tree memory limit of 12 GiB.

The archived environment records do not document background workload
isolation or power-plan settings. Process isolation for each benchmark run
does not imply that unrelated system workloads were disabled.
