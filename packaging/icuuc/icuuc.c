/* A forwarder for the ICU functions Qt needs, for systems without an icuuc.dll of their own.
 *
 * Windows 10 and later have icu.dll and an icuuc.dll that does nothing but forward to it. Valve's
 * Proton builds (the Steam Deck's) ship icu.dll but not icuuc.dll, so Qt6Core.dll, which imports
 * icuuc.dll, cannot load there. This library is that missing file: it has no code of its own,
 * only the export table of icuuc.def, whose entries forward to icu.dll. The generator puts its
 * folder on the DLL search path only when the system lacks icuuc.dll (rnw.gui.windows_icu).
 */

#include <windows.h>

BOOL WINAPI DllMain(HINSTANCE instance, DWORD reason, LPVOID reserved)
{
    (void)instance, (void)reason, (void)reserved;
    return TRUE;
}
