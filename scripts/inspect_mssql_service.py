import winreg
key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Services")
sub = winreg.OpenKey(key, "MSSQL$SQLEXPRESS")
i = 0
while True:
    try:
        n, v, _ = winreg.EnumValue(sub, i)
        print(f"{n}: {v}")
        i += 1
    except WindowsError:
        break
