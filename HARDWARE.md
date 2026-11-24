# Benchmark computer inventory

The definitive raw environment files currently record:

- operating system: Windows 11, build string `Windows-11-10.0.26200-SP0`;
- balanced run: Anaconda Python 3.12.15, 64 bit;
- challenge run: Anaconda Python 3.12.16, 64 bit;
- processor identifier: `Intel64 Family 6 Model 183 Stepping 1, GenuineIntel`;
- per-process-tree memory limit: 12 GiB;
- per-run wall-time limit: 600 seconds.

## Supplied computer specifications

The following specifications were supplied by the authors from the Windows
system-information screen; they have not been independently measured by the
benchmark scripts:

- **Processor:** 13th Gen Intel Core i7-13700, displayed at 2.10 GHz.
- **Computer:** Dell OptiPlex SFF Plus 7010.
- **CPU topology:** 16 physical cores and 24 logical processors, as reported by Windows.
- **Installed RAM:** 32.0 GB (31.7 GB usable).
- **System type:** 64-bit operating system, x64-based processor.
- **Graphics:** Intel UHD Graphics 770 (128 MB shown).
- **Storage:** Windows PowerShell reports two KIOXIA BG6 1024 GB NVMe SSDs.
  The C: volume is on physical disk 0, one of those SSDs.

The raw environment files above remain unchanged. Please confirm that these
hardware details are from the machine used for
both the balanced and challenge definitive experiments.

## Still to verify

- **Workload isolation:** `[STATE WHETHER OTHER APPLICATIONS, SYNCHRONIZATION,
  ANTIVIRUS SCANS AND POWER-SAVING MODES WERE DISABLED]`
- **Power plan and whether the computer was connected to AC power:**
  `[TO BE PROVIDED]`

Useful PowerShell commands on the benchmark computer:

```powershell
Get-CimInstance Win32_Processor |
  Select-Object Name, NumberOfCores, NumberOfLogicalProcessors

Get-CimInstance Win32_ComputerSystem |
  Select-Object Manufacturer, Model, TotalPhysicalMemory

Get-PhysicalDisk |
  Select-Object FriendlyName, MediaType, BusType, Size
```

Do not replace the original `environment.json` files. Add the verified hardware
information here and in the manuscript so the archived raw record remains
unaltered.

