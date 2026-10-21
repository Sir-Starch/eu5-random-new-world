/* Random New World Generator: opens the generator's window from the mod's folder (ADR 0009).
 *
 * It sits at the top of the mod folder and starts
 *     generator\python\pythonw.exe -B -I -X utf8 -m rnw.gui <its own arguments>
 * in the generator folder, with output and errors going to launcher.log in the generator's
 * data folder (%LOCALAPPDATA%\RandomNewWorld). If Python cannot start, or stops with an error
 * within the first seconds, it shows the end of that log. It does nothing else.
 */

#ifndef UNICODE
#define UNICODE
#endif
#define _WIN32_WINNT 0x0A00
#include <windows.h>
#include <shlobj.h>
#include <stdarg.h>
#include <stdio.h>
#include <wchar.h>

#define TITLE L"Random New World Generator"
#define PATH_CHARS 4096
#define COMMAND_CHARS 32768
#define MESSAGE_CHARS 8192
#define WATCH_MILLISECONDS 20000
#define TAIL_BYTES 3000

static wchar_t folder[PATH_CHARS];
static wchar_t generator[PATH_CHARS];
static wchar_t python[PATH_CHARS];
static wchar_t log_path[PATH_CHARS];
static wchar_t command[COMMAND_CHARS];
static wchar_t message[MESSAGE_CHARS];

static void complain(void)
{
    MessageBoxW(NULL, message, TITLE, MB_OK | MB_ICONERROR);
}

static void format(wchar_t *target, size_t size, const wchar_t *pattern, ...)
{
    va_list values;
    va_start(values, pattern);
    _vsnwprintf(target, size - 1, pattern, values);
    va_end(values);
    target[size - 1] = 0;
}

/* The launcher's own command line without its program name, passed on to the window. */
static const wchar_t *own_arguments(const wchar_t *line)
{
    if (*line == L'"') {
        ++line;
        while (*line != 0 && *line != L'"') {
            ++line;
        }
        if (*line == L'"') {
            ++line;
        }
    } else {
        while (*line != 0 && *line != L' ' && *line != L'\t') {
            ++line;
        }
    }
    while (*line == L' ' || *line == L'\t') {
        ++line;
    }
    return line;
}

static BOOL find_folder(void)
{
    DWORD length = GetModuleFileNameW(NULL, folder, PATH_CHARS);
    wchar_t *slash = length > 0 && length < PATH_CHARS ? wcsrchr(folder, L'\\') : NULL;
    if (slash == NULL) {
        return FALSE;
    }
    *slash = 0;
    return TRUE;
}

static HANDLE open_log(void)
{
    wchar_t *base = NULL;
    if (FAILED(SHGetKnownFolderPath(&FOLDERID_LocalAppData, 0, NULL, &base))) {
        return INVALID_HANDLE_VALUE;
    }
    format(log_path, PATH_CHARS, L"%ls\\RandomNewWorld", base);
    CoTaskMemFree(base);
    CreateDirectoryW(log_path, NULL);
    format(log_path + wcslen(log_path), PATH_CHARS - wcslen(log_path), L"\\launcher.log");
    SECURITY_ATTRIBUTES inherited = {.nLength = sizeof inherited, .bInheritHandle = TRUE};
    return CreateFileW(log_path, GENERIC_WRITE, FILE_SHARE_READ | FILE_SHARE_WRITE, &inherited,
                       CREATE_ALWAYS, FILE_ATTRIBUTE_NORMAL, NULL);
}

static void explain_exit(DWORD code)
{
    static char bytes[TAIL_BYTES + 1];
    static wchar_t tail[TAIL_BYTES + 1];
    DWORD read = 0;
    HANDLE file = CreateFileW(log_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE, NULL,
                              OPEN_EXISTING, FILE_ATTRIBUTE_NORMAL, NULL);
    if (file != INVALID_HANDLE_VALUE) {
        LARGE_INTEGER size;
        if (GetFileSizeEx(file, &size) && size.QuadPart > TAIL_BYTES) {
            LARGE_INTEGER start = {.QuadPart = size.QuadPart - TAIL_BYTES};
            SetFilePointerEx(file, start, NULL, FILE_BEGIN);
        }
        if (!ReadFile(file, bytes, TAIL_BYTES, &read, NULL)) {
            read = 0;
        }
        CloseHandle(file);
    }
    int chars = MultiByteToWideChar(CP_UTF8, 0, bytes, (int)read, tail, TAIL_BYTES);
    tail[chars > 0 ? chars : 0] = 0;
    format(message, MESSAGE_CHARS,
           L"The generator stopped with an error (exit code %lu).\n\nIts log: %ls\n\n%ls", code,
           log_path[0] != 0 ? log_path : L"(none could be written)", tail);
    complain();
}

int WINAPI wWinMain(HINSTANCE instance, HINSTANCE previous, PWSTR arguments, int show)
{
    (void)instance, (void)previous, (void)arguments, (void)show;
    if (!find_folder()) {
        format(message, MESSAGE_CHARS, L"This program cannot find its own folder.");
        complain();
        return 2;
    }
    format(generator, PATH_CHARS, L"%ls\\generator", folder);
    format(python, PATH_CHARS, L"%ls\\python\\pythonw.exe", generator);
    if (GetFileAttributesW(python) == INVALID_FILE_ATTRIBUTES) {
        format(message, MESSAGE_CHARS,
               L"The generator is incomplete: %ls is missing.\n\nUnsubscribe from Random New "
               L"World and subscribe again so that Steam downloads it whole.",
               python);
        complain();
        return 2;
    }
    HANDLE output = open_log();
    BOOL logged = output != INVALID_HANDLE_VALUE;
    format(command, COMMAND_CHARS, L"\"%ls\" -B -I -X utf8 -m rnw.gui %ls", python,
           own_arguments(GetCommandLineW()));
    STARTUPINFOW startup = {.cb = sizeof startup};
    if (logged) {
        startup.dwFlags = STARTF_USESTDHANDLES;
        startup.hStdOutput = output;
        startup.hStdError = output;
    }
    PROCESS_INFORMATION process;
    if (!CreateProcessW(python, command, NULL, NULL, logged, 0, NULL, generator, &startup,
                        &process)) {
        DWORD error = GetLastError();
        static wchar_t reason[512];
        if (FormatMessageW(FORMAT_MESSAGE_FROM_SYSTEM | FORMAT_MESSAGE_IGNORE_INSERTS, NULL, error,
                           0, reason, 512, NULL) == 0) {
            reason[0] = 0;
        }
        format(message, MESSAGE_CHARS, L"Windows could not start %ls (error %lu). %ls", python,
               error, reason);
        complain();
        return 2;
    }
    if (logged) {
        CloseHandle(output);
    }
    CloseHandle(process.hThread);
    DWORD code = 0;
    if (WaitForSingleObject(process.hProcess, WATCH_MILLISECONDS) == WAIT_OBJECT_0 &&
        GetExitCodeProcess(process.hProcess, &code) && code != 0) {
        explain_exit(code);
    }
    CloseHandle(process.hProcess);
    return (int)code;
}
