/* Experiment 019, part 3: a harmless Windows program started from the game's Open in folder.
 *
 * It writes probe-result.txt next to itself (where it runs, what Wine it is under, the cores
 * and the free memory beside the running game, the profile and Steam library the generator
 * would use) and then shows a message box. It changes nothing else and opens no network.
 *
 * Build: x86_64-w64-mingw32-gcc -std=c11 -Wall -Wextra -Wpedantic -Wconversion -O2 -s -municode -mwindows -o probe.exe probe.c -lshell32 -lole32 -luuid
 */

#define _WIN32_WINNT 0x0A00
#ifndef UNICODE
#define UNICODE
#endif
#include <windows.h>
#include <shlobj.h>
#include <stdarg.h>
#include <stdio.h>
#include <wchar.h>

#define PROBE_VERSION L"1"
#define REPORT_CHARS 16384

static wchar_t report[REPORT_CHARS];
static size_t used;

static void line(const wchar_t *format, ...)
{
    va_list args;
    va_start(args, format);
    int written = _vsnwprintf(report + used, REPORT_CHARS - used - 2, format, args);
    va_end(args);
    if (written > 0) {
        used += (size_t)written;
        report[used++] = L'\n';
        report[used] = 0;
    }
}

static const wchar_t *exists(const wchar_t *path)
{
    return GetFileAttributesW(path) == INVALID_FILE_ATTRIBUTES ? L"missing" : L"exists";
}

static void wine(const wchar_t *own_path)
{
    HMODULE ntdll = GetModuleHandleW(L"ntdll.dll");
    HMODULE kernel32 = GetModuleHandleW(L"kernel32.dll");
    typedef const char *(CDECL *version_fn)(void);
    typedef void(CDECL *host_fn)(const char **, const char **);
    typedef char *(CDECL *unix_fn)(const wchar_t *);
    version_fn version = (version_fn)(void (*)(void))GetProcAddress(ntdll, "wine_get_version");
    host_fn host = (host_fn)(void (*)(void))GetProcAddress(ntdll, "wine_get_host_version");
    unix_fn unix_name = (unix_fn)(void (*)(void))GetProcAddress(kernel32, "wine_get_unix_file_name");
    if (version == NULL) {
        line(L"wine: no (real Windows)");
        return;
    }
    line(L"wine: %hs", version());
    if (host != NULL) {
        const char *system = "?", *release = "?";
        host(&system, &release);
        line(L"host: %hs %hs", system, release);
    }
    if (unix_name != NULL) {
        char *path = unix_name(own_path);
        if (path != NULL) {
            line(L"unix path: %hs", path);
            HeapFree(GetProcessHeap(), 0, path);
        }
    }
}

static void windows_version(void)
{
    typedef LONG(WINAPI *rtl_fn)(OSVERSIONINFOW *);
    rtl_fn get = (rtl_fn)(void (*)(void))GetProcAddress(GetModuleHandleW(L"ntdll.dll"), "RtlGetVersion");
    OSVERSIONINFOW info = {.dwOSVersionInfoSize = sizeof info};
    if (get != NULL && get(&info) == 0) {
        line(L"windows: %lu.%lu build %lu", info.dwMajorVersion, info.dwMinorVersion,
             info.dwBuildNumber);
    }
}

static void machine(void)
{
    DWORD_PTR process = 0, system = 0;
    int allowed = 0;
    if (GetProcessAffinityMask(GetCurrentProcess(), &process, &system)) {
        for (DWORD_PTR mask = process; mask != 0; mask &= mask - 1) {
            ++allowed;
        }
    }
    line(L"processors: %lu active, %d in affinity", GetActiveProcessorCount(ALL_PROCESSOR_GROUPS),
         allowed);
    MEMORYSTATUSEX memory = {.dwLength = sizeof memory};
    if (GlobalMemoryStatusEx(&memory)) {
        line(L"memory: %llu MiB total, %llu MiB available, load %lu%%",
             memory.ullTotalPhys >> 20, memory.ullAvailPhys >> 20, memory.dwMemoryLoad);
    }
}

static void places(void)
{
    static const wchar_t *const names[] = {L"SteamAppId", L"SteamGameId", L"STEAM_COMPAT_DATA_PATH",
                                           L"WINEPREFIX"};
    wchar_t value[1024];
    for (size_t i = 0; i < sizeof names / sizeof names[0]; ++i) {
        DWORD length = GetEnvironmentVariableW(names[i], value, 1024);
        line(L"env %ls: %ls", names[i], length > 0 && length < 1024 ? value : L"(not set)");
    }
    wchar_t *documents = NULL;
    if (SUCCEEDED(SHGetKnownFolderPath(&FOLDERID_Documents, 0, NULL, &documents))) {
        wchar_t profile[MAX_PATH * 2];
        _snwprintf(profile, MAX_PATH * 2, L"%ls\\Paradox Interactive\\Europa Universalis V\\mod",
                   documents);
        line(L"documents: %ls", documents);
        line(L"profile mod folder: %ls", exists(profile));
        CoTaskMemFree(documents);
    }
    static const wchar_t *const steam[] = {
        L"C:\\Program Files (x86)\\Steam\\steamapps\\libraryfolders.vdf",
        L"S:\\steamapps\\common\\Europa Universalis V\\binaries\\eu5.exe",
    };
    for (size_t i = 0; i < sizeof steam / sizeof steam[0]; ++i) {
        line(L"%ls: %ls", steam[i], exists(steam[i]));
    }
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show)
{
    (void)instance, (void)previous, (void)arguments, (void)show;
    wchar_t own[MAX_PATH * 2];
    DWORD length = GetModuleFileNameW(NULL, own, MAX_PATH * 2);
    SYSTEMTIME now;
    GetLocalTime(&now);
    line(L"Random New World launch probe %ls", PROBE_VERSION);
    line(L"time: %04u-%02u-%02u %02u:%02u:%02u", now.wYear, now.wMonth, now.wDay, now.wHour,
         now.wMinute, now.wSecond);
    line(L"program: %ls", own);
    wchar_t directory[MAX_PATH * 2];
    GetCurrentDirectoryW(MAX_PATH * 2, directory);
    line(L"current directory: %ls", directory);
    wine(own);
    windows_version();
    machine();
    places();

    wchar_t result[MAX_PATH * 2];
    wcscpy(result, own);
    wchar_t *slash = wcsrchr(result, L'\\');
    wcscpy(slash != NULL && length > 0 ? slash + 1 : result, L"probe-result.txt");
    int bytes = WideCharToMultiByte(CP_UTF8, 0, report, (int)used, NULL, 0, NULL, NULL);
    char *text = HeapAlloc(GetProcessHeap(), 0, (SIZE_T)bytes + 1);
    WideCharToMultiByte(CP_UTF8, 0, report, (int)used, text, bytes, NULL, NULL);
    HANDLE file = CreateFileW(result, GENERIC_WRITE, 0, NULL, CREATE_ALWAYS,
                              FILE_ATTRIBUTE_NORMAL, NULL);
    DWORD written = 0;
    BOOL saved = file != INVALID_HANDLE_VALUE && WriteFile(file, text, (DWORD)bytes, &written, NULL)
                 && written == (DWORD)bytes;
    DWORD error = saved ? 0 : GetLastError();
    if (file != INVALID_HANDLE_VALUE) {
        CloseHandle(file);
    }

    wchar_t message[REPORT_CHARS + 512];
    _snwprintf(message, REPORT_CHARS + 512, L"%ls\n%ls %ls (error %lu)", report,
               saved ? L"Written to" : L"Could NOT write", result, error);
    MessageBoxW(NULL, message, L"Random New World: launch probe", MB_OK | MB_ICONINFORMATION);
    return saved ? 0 : 1;
}
