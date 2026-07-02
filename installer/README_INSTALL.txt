FAISAL CLINICAL LABORATORY
Laboratory Information System - Installation Guide
Version 2.2.0

------------------------------------------------------------
HOW TO INSTALL
------------------------------------------------------------

1. Double-click "FaisalClinicalLaboratory-Setup-2.2.0.exe".
2. If Windows asks for permission (User Account Control), click Yes.
   Administrator rights are required because the program installs into
   the Program Files folder.
3. Read and accept the license agreement.
4. Confirm the installation folder (default is recommended):
       C:\Program Files\Faisal Clinical Laboratory
5. Choose whether to create a desktop shortcut.
6. Click Install and wait for the files to be copied.
7. Click Finish. You can launch the program immediately, from the
   Start Menu, or from the desktop shortcut.

------------------------------------------------------------
MINIMUM WINDOWS VERSION
------------------------------------------------------------

- Windows 10 (64-bit) or Windows 11 (64-bit).
- No separate Python installation is required; everything needed to run
  the program is included.

------------------------------------------------------------
HOW TO UNINSTALL
------------------------------------------------------------

Uninstall in either of these ways:

- Settings > Apps > Installed apps > "Faisal Clinical Laboratory" >
  Uninstall, OR
- Start Menu > "Uninstall Faisal Clinical Laboratory".

During uninstall you will be asked:

   "Do you want to remove all saved reports?"

   - Choose NO to keep your saved reports on disk.
   - Choose YES to permanently delete the reports folder.

Your laboratory settings (settings.json) are kept during uninstall so that
re-installing later restores your branding and report numbering.

------------------------------------------------------------
WHERE REPORTS ARE STORED
------------------------------------------------------------

Saved reports are stored in:

   C:\Program Files\Faisal Clinical Laboratory\_internal\reports

(If you chose a different installation folder, replace the path above
accordingly.)

Tip: Back up this folder regularly.

------------------------------------------------------------
WHERE SETTINGS ARE STORED
------------------------------------------------------------

Laboratory settings - name, address, logo, signature, footer, report
prefix and the current report number - are stored in:

   C:\Program Files\Faisal Clinical Laboratory\_internal\data\settings.json

------------------------------------------------------------
HOW TO UPGRADE
------------------------------------------------------------

To upgrade to a newer version, simply run the new installer. Install it
into the SAME folder as the existing version (the installer selects this
automatically).

Your data is preserved during an upgrade:

   - Saved reports (the reports folder) are NOT deleted.
   - Laboratory settings (settings.json) are NOT overwritten, so your
     branding and report numbering carry over unchanged.

Only the program files (application, libraries, and the medical test
catalog) are updated.

------------------------------------------------------------
SUPPORT
------------------------------------------------------------

For assistance, contact Faisal Clinical Laboratory.
