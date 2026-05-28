using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;

[assembly: AssemblyTitle("USART HMI Host Automation")]
[assembly: AssemblyProduct("USART HMI Host Automation")]
[assembly: AssemblyCompany("Codex")]
[assembly: AssemblyVersion("1.67.6.3035")]
[assembly: AssemblyFileVersion("1.67.6.3035")]
[assembly: AssemblyInformationalVersion("1.67.6.3035")]

internal static class UsartHmiHostAutomation
{
    private const string ARG_NONE = "__CODEX_NONE__";
    private static string installDir;
    private static string hmiPath;
    private static string reportPath;
    private static string tracePath;
    private static string pageResource;
    private static string patchSpecPath;
    private static string pageDumpPath;
    private static string createControlVarName;
    private static string addPageName;
    private static string compileOutputPath;
    private static string macroSpecPath;
    private static string appMedataStringHint;
    private static int ram1OpenHint = -1;
    private static bool forceSaveProject;
    private static bool forcePageDump;
    private static int pageIndex;
    private static int objectIndex;
    private static DateTime deadlineUtc;
    private static Timer pollTimer;
    private static Timer createModalCloseTimer;
    private static bool handled;
    private static string failureMessage;
    private static string openedPageName;
    private static int openedPageId = -1;
    private static string canvasSelectedObjname;
    private static string attributeSelectedObjname;
    private static string gridObjnameValue;
    private static int propertyGridRowCount;
    private static string comboSelectedText;
    private static string appMedataString;
    private static string appMedataHex;
    private static int ram1Open = -1;
    private static bool managedCompileOk;
    private static string managedCompileText;
    private static long managedCompileBytes = -1;
    private static bool savedProjectOk;
    private static string lastFormsSnapshot;
    private static int macroActionCount;
    private static List<string> resourcesPageNames = new List<string>();
    private static int createBeforeObjectCount = -1;
    private static int resourcesPageCount = -1;
    private static int resourcesPageCountBeforeAdd = -1;
    private static int resourcesPageCountAfterAdd = -1;
    private static DateTime startupDialogCloseAllowedUtc;

    [STAThread]
    private static int Main(string[] args)
    {
        try
        {
            if (args.Length < 4)
            {
                Console.Error.WriteLine("usage: UsartHmiHostAutomation.exe <hmi_path> <page_index> <object_index> <report_json> [install_dir] [page_resource] [patch_spec_path] [create_control_var_name] [compile_output_path] [appmedata_string] [ram1_open] [force_save] [force_page_dump] [add_page_name] [macro_spec_path]");
                return 2;
            }

            hmiPath = Path.GetFullPath(args[0]);
            pageIndex = int.Parse(args[1]);
            objectIndex = int.Parse(args[2]);
            reportPath = Path.GetFullPath(args[3]);
            tracePath = reportPath + ".trace.log";
            pageDumpPath = reportPath + ".page.bin";
            installDir = args.Length >= 5 ? Path.GetFullPath(args[4]) : @"C:\Program Files (x86)\USART HMI";
            pageResource = args.Length >= 6 && args[5] != ARG_NONE ? args[5] : "";
            patchSpecPath = args.Length >= 7 && args[6] != ARG_NONE && !string.IsNullOrEmpty(args[6]) ? Path.GetFullPath(args[6]) : null;
            createControlVarName = args.Length >= 8 && args[7] != ARG_NONE && !string.IsNullOrEmpty(args[7]) ? args[7] : "";
            compileOutputPath = args.Length >= 9 && args[8] != ARG_NONE && !string.IsNullOrEmpty(args[8]) ? Path.GetFullPath(args[8]) : "";
            appMedataStringHint = args.Length >= 10 && args[9] != ARG_NONE ? args[9].Replace("\\n", "\n").Replace("\\r", "\r") : "";
            ram1OpenHint = args.Length >= 11 && args[10] != ARG_NONE ? int.Parse(args[10]) : -1;
            forceSaveProject = args.Length >= 12 && args[11] != ARG_NONE && ParseBoolArg(args[11]);
            forcePageDump = args.Length >= 13 && args[12] != ARG_NONE && ParseBoolArg(args[12]);
            addPageName = args.Length >= 14 && args[13] != ARG_NONE && !string.IsNullOrEmpty(args[13]) ? args[13] : "";
            macroSpecPath = args.Length >= 15 && args[14] != ARG_NONE && !string.IsNullOrEmpty(args[14]) ? Path.GetFullPath(args[14]) : "";
            deadlineUtc = DateTime.UtcNow.AddSeconds(45.0);
            startupDialogCloseAllowedUtc = DateTime.UtcNow.AddSeconds(6.5);
            Trace("start hmi=" + hmiPath + " page=" + pageIndex + " pageResource=" + pageResource + " objectIndex=" + objectIndex + " createControl=" + createControlVarName + " addPage=" + addPageName + " macroSpec=" + macroSpecPath + " compileOutput=" + compileOutputPath + " install=" + installDir + " ram1Hint=" + ram1OpenHint + " forceSave=" + forceSaveProject + " forcePageDump=" + forcePageDump + " appmedataHint=" + SafeString(appMedataStringHint));

            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Trace("winforms initialized");

            BootstrapOfficialRuntime();
            Trace("official runtime bootstrapped");
            EnsureSoftOpenFlags();
            Trace("soft-open feature flags primed");

            pollTimer = new Timer();
            pollTimer.Interval = 100;
            pollTimer.Tick += new EventHandler(PollTimer_Tick);
            pollTimer.Start();
            Trace("poll timer started");

            Trace("invoking HMIFORM.Program.RunMain");
            InvokeHmiformRunMain();
            Trace("HMIFORM.Program.RunMain returned");
            if (!handled)
            {
                failureMessage = "HMIFORM.Program.RunMain returned before automation completed";
                WriteReport();
                Environment.Exit(1);
                return 1;
            }
            Environment.Exit(failureMessage == null ? 0 : 1);
            return failureMessage == null ? 0 : 1;
        }
        catch (Exception ex)
        {
            failureMessage = FlattenException(ex);
            WriteReport();
            Console.Error.WriteLine(failureMessage);
            return 100;
        }
    }

    private static void PollTimer_Tick(object sender, EventArgs e)
    {
        try
        {
            if (handled)
            {
                return;
            }
            CloseBlockingForms(true, false, true);
            TraceFormsSnapshot();
            if (DateTime.UtcNow > deadlineUtc)
            {
                handled = true;
                failureMessage = "Timed out waiting for HMIFORM.main";
                StopTimer();
                StopCreateModalCloseTimer();
                WriteReport();
                Application.ExitThread();
                return;
            }

            Form mainForm = FindMainForm();
            if (mainForm == null)
            {
                return;
            }

            Trace("found HMIFORM.main");
            handled = true;
            StopTimer();
            RunAutomation(mainForm);
        }
        catch (Exception ex)
        {
            handled = true;
            StopTimer();
            StopCreateModalCloseTimer();
            failureMessage = FlattenException(ex);
            WriteReport();
            Application.ExitThread();
        }
    }

    private static void RunAutomation(Form mainForm)
    {
        try
        {
            bool hasPatchSpec = !string.IsNullOrEmpty(patchSpecPath) && File.Exists(patchSpecPath);
            bool hasMacroSpec = !string.IsNullOrEmpty(macroSpecPath) && File.Exists(macroSpecPath);
            bool hasAddPage = !string.IsNullOrEmpty(addPageName);
            bool hasObjectSelection = objectIndex >= 0;
            bool compileOnlyProbe =
                string.IsNullOrEmpty(createControlVarName)
                && !hasAddPage
                && !hasMacroSpec
                && !hasPatchSpec
                && !forcePageDump
                && !string.IsNullOrEmpty(compileOutputPath);
            PrimeOfficialRuntimeState();
            ConditionDelegate startupCondition = compileOnlyProbe
                ? new ConditionDelegate(IsProjectLoaded)
                : new ConditionDelegate(IsMainPageReady);
            string startupLabel = compileOnlyProbe ? "project-loaded" : "ready";
            bool startupReady = TryWaitForCondition(startupCondition, mainForm, 20.0);
            if (!startupReady)
            {
                Trace("startup auto-open did not reach " + startupLabel + " state, falling back to filecaozuo(open)");
                CloseBlockingForms(true, true, false);
                StartCreateModalCloseTimer();
                bool opened;
                try
                {
                    opened = (bool)InvokeMethod(mainForm, "filecaozuo", new object[] { "open", hmiPath });
                }
                finally
                {
                    StopCreateModalCloseTimer();
                }
                Trace("filecaozuo(open) returned " + opened);
                if (!opened)
                {
                    throw new InvalidOperationException("filecaozuo(open) returned false");
                }
                WaitForCondition(startupCondition, mainForm, 20.0, startupLabel + " after open");
            }
            else
            {
                Trace("startup auto-open reached " + startupLabel + " state");
            }
            RestoreManagedAppMetadata(mainForm);
            CloseBlockingForms(true, true, false);

            if (hasMacroSpec)
            {
                RunMacroSpec(mainForm);
                CaptureState(mainForm);
                Trace("macro completed pages=" + resourcesPageCount + " canvas=" + SafeString(canvasSelectedObjname) + " attr=" + SafeString(attributeSelectedObjname));
                WriteReport();
                return;
            }

            if (hasAddPage)
            {
                pageIndex = AddPage(mainForm, addPageName);
                pageResource = "";
                CaptureState(mainForm);
                Trace("add-page completed name=" + SafeString(openedPageName) + " id=" + openedPageId + " count=" + resourcesPageCountAfterAdd);
            }

            if (!compileOnlyProbe)
            {
                if (pageIndex >= 0)
                {
                    pageIndex = ResolveRuntimePageIndex(mainForm, pageResource, pageIndex);
                    object pageAdmin = GetField(mainForm, "pageadmin1");
                    Trace("selecting page " + pageIndex);
                    InvokeMethod(pageAdmin, "selectindex", new object[] { pageIndex });
                    WaitForCondition(new ConditionDelegate(IsRequestedPageReady), mainForm, 10.0, "page selection");
                    Trace("page selection ready");
                }
                else
                {
                    WaitForCondition(new ConditionDelegate(IsMainPageReady), mainForm, 10.0, "main page ready");
                }
                Trace("main page ready");

                if (!string.IsNullOrEmpty(createControlVarName))
                {
                    CreateControl(mainForm, createControlVarName);
                }
                else
                {
                    if (hasObjectSelection)
                    {
                        object tftEdit = GetField(mainForm, "TFTEDIT0");
                        Trace("invoking setxuanzhong_del/setxuanzhong_add for objectIndex=" + objectIndex);
                        InvokeMethod(tftEdit, "setxuanzhong_del", new object[] { 0 });
                        InvokeMethod(tftEdit, "setxuanzhong_add", new object[] { objectIndex });
                        InvokeMethod(mainForm, "objselect", null);
                        Application.DoEvents();
                        Trace("objselect invoked");
                    }
                    else
                    {
                        Trace("no object selection requested");
                    }
                }

                if (hasPatchSpec)
                {
                    ApplyPatchSpec(mainForm);
                    InvokeMethod(mainForm, "objselect", null);
                    Application.DoEvents();
                    Trace("patch spec applied");
                }

                CaptureState(mainForm);
                Trace("captured state canvas=" + SafeString(canvasSelectedObjname) + " attr=" + SafeString(attributeSelectedObjname) + " grid=" + SafeString(gridObjnameValue));
                if ((hasObjectSelection || !string.IsNullOrEmpty(createControlVarName) || hasPatchSpec) && (attributeSelectedObjname == null || attributeSelectedObjname.Length == 0))
                {
                    throw new InvalidOperationException("objatt2 selection did not populate after objselect()");
                }
            }
            else
            {
                Trace("compile-only probe: skipping page/object selection");
                CaptureState(mainForm);
            }

            bool shouldPersistProject = forceSaveProject || hasAddPage || (!string.IsNullOrEmpty(createControlVarName)) || hasPatchSpec;
            if (shouldPersistProject)
            {
                PersistProject(mainForm);
            }

            bool shouldDumpPage = forcePageDump || (!hasAddPage && shouldPersistProject);
            if (shouldDumpPage)
            {
                bool dumped = DumpCurrentPage(mainForm);
                Trace("DumpCurrentPage() returned " + dumped);
                if (!dumped)
                {
                    throw new InvalidOperationException("DumpCurrentPage() returned false");
                }
            }

            if (!string.IsNullOrEmpty(compileOutputPath))
            {
                managedCompileOk = RunManagedCompile(mainForm, compileOutputPath);
                Trace("RunManagedCompile() returned " + managedCompileOk + " bytes=" + managedCompileBytes);
            }

            WriteReport();
        }
        catch (Exception ex)
        {
            failureMessage = FlattenException(ex);
            WriteReport();
        }
        finally
        {
            StopCreateModalCloseTimer();
            try
            {
                BeginClose(mainForm);
            }
            catch
            {
                Application.ExitThread();
            }
        }
    }

    private static void PrimeOfficialRuntimeState()
    {
        try
        {
            Type win32Type = FindType("hmitype.Win32");
            MethodInfo getHmiver = win32Type.GetMethod("gethmiver", BindingFlags.Public | BindingFlags.Static);
            if (getHmiver == null)
            {
                Trace("hmitype.Win32.gethmiver not found");
                return;
            }
            Trace("invoking hmitype.Win32.gethmiver");
            getHmiver.Invoke(null, new object[] { 1500, 4000, 1 });
            Trace("hmitype.Win32.gethmiver completed");
        }
        catch (Exception ex)
        {
            Trace("hmitype.Win32.gethmiver failed: " + FlattenException(ex));
        }
    }

    private static void EnsureSoftOpenFlags()
    {
        bool requireMedata = (appMedataStringHint != null && appMedataStringHint.Length > 0) || ram1OpenHint == 1;
        bool require3DPrinter = !string.IsNullOrEmpty(createControlVarName) && string.Equals(createControlVarName, "Printer3D", StringComparison.OrdinalIgnoreCase);
        if (!requireMedata && !require3DPrinter)
        {
            return;
        }
        object hmiData = GetStaticField("hmitype.AppData", "HMIData0");
        if (hmiData == null)
        {
            Trace("hmitype.AppData.HMIData0 unavailable");
            return;
        }
        if (requireMedata)
        {
            try
            {
                SetField(hmiData, "SoftOpen_MedataMakeEn", (byte)1);
                Trace("set AppData.HMIData0.SoftOpen_MedataMakeEn=1");
            }
            catch (Exception ex)
            {
                Trace("set SoftOpen_MedataMakeEn failed: " + FlattenException(ex));
            }
        }
        if (require3DPrinter)
        {
            try
            {
                SetField(hmiData, "SoftOpen_3DprinterEn", (byte)1);
                Trace("set AppData.HMIData0.SoftOpen_3DprinterEn=1");
            }
            catch (Exception ex)
            {
                Trace("set SoftOpen_3DprinterEn failed: " + FlattenException(ex));
            }
        }
    }

    private static void PersistProject(Form mainForm)
    {
        CloseBlockingForms(true, true, false);
        StartCreateModalCloseTimer();
        try
        {
            bool saved = (bool)InvokeMethod(mainForm, "filecaozuo", new object[] { "save", "" });
            Trace("filecaozuo(save) returned " + saved);
            savedProjectOk = saved;
            if (!saved)
            {
                throw new InvalidOperationException("filecaozuo(save) returned false");
            }
        }
        finally
        {
            StopCreateModalCloseTimer();
        }
    }

    private static void RestoreManagedAppMetadata(Form mainForm)
    {
        if ((appMedataStringHint == null || appMedataStringHint.Length == 0) && ram1OpenHint < 0)
        {
            return;
        }
        object myapp = GetField(mainForm, "Myapp");
        if (myapp == null)
        {
            return;
        }
        if (appMedataStringHint != null && appMedataStringHint.Length > 0)
        {
            bool ok = (bool)InvokeMethod(myapp, "APPMEDATA_Setstring", new object[] { appMedataStringHint });
            Trace("restore APPMEDATA_Setstring => " + ok + " value=" + SafeString(appMedataStringHint));
        }
        if (ram1OpenHint == 1)
        {
            EnsureRam1Open(myapp);
        }
    }

    private static void CreateControl(Form mainForm, string controlVarName)
    {
        object appobjs = GetStaticField("hmitype.AppData", "appobjs");
        if (appobjs == null)
        {
            throw new InvalidOperationException("hmitype.AppData.appobjs is null");
        }
        object objmark = GetField(appobjs, controlVarName);
        if (objmark == null)
        {
            throw new InvalidOperationException("Unknown appobjs control var: " + controlVarName);
        }
        object dpage = GetField(mainForm, "dpage");
        createBeforeObjectCount = ReadPageObjectCount(dpage);
        Trace("invoking AddObj for control var " + controlVarName + " beforeCount=" + createBeforeObjectCount);
        StartCreateModalCloseTimer();
        InvokeMethod(mainForm, "AddObj", new object[] { objmark });
        StopCreateModalCloseTimer();
        WaitForCondition(new ConditionDelegate(IsObjectCountIncreased), mainForm, 10.0, "managed AddObj");
        objectIndex = ReadCurrentSelectedObjectIndex(mainForm);
        Trace("managed AddObj selected objectIndex=" + objectIndex);
        InvokeMethod(mainForm, "objselect", null);
        Application.DoEvents();
        EnsureVpAddressSpace(mainForm);
    }

    private static void RunMacroSpec(Form mainForm)
    {
        string[] lines = File.ReadAllLines(macroSpecPath, Encoding.UTF8);
        int i;
        for (i = 0; i < lines.Length; i++)
        {
            string rawLine = lines[i];
            string line = rawLine.Trim();
            if (line.Length == 0 || line.StartsWith("#"))
            {
                continue;
            }
            string[] parts = rawLine.Split(new char[] { '\t' });
            if (parts.Length == 0)
            {
                continue;
            }
            string op = parts[0];
            macroActionCount++;
            Trace("macro[" + macroActionCount + "] " + rawLine);
            if (op == "select-page")
            {
                if (parts.Length < 3)
                {
                    throw new InvalidOperationException("select-page requires page_index and page_resource");
                }
                pageIndex = ResolveRuntimePageIndex(mainForm, parts[2], int.Parse(parts[1]));
                pageResource = parts[2];
                object pageAdmin = GetField(mainForm, "pageadmin1");
                InvokeMethod(pageAdmin, "selectindex", new object[] { pageIndex });
                WaitForCondition(new ConditionDelegate(IsRequestedPageReady), mainForm, 10.0, "macro select-page");
                continue;
            }
            if (op == "select-object")
            {
                if (parts.Length < 2)
                {
                    throw new InvalidOperationException("select-object requires object_index");
                }
                objectIndex = int.Parse(parts[1]);
                SelectObject(mainForm, objectIndex);
                continue;
            }
            if (op == "add-page")
            {
                if (parts.Length < 2)
                {
                    throw new InvalidOperationException("add-page requires page name");
                }
                addPageName = parts[1];
                pageIndex = AddPage(mainForm, addPageName);
                pageResource = "";
                continue;
            }
            if (op == "create-control")
            {
                if (parts.Length < 2)
                {
                    throw new InvalidOperationException("create-control requires control var name");
                }
                createControlVarName = parts[1];
                CreateControl(mainForm, createControlVarName);
                continue;
            }
            if (op == "patch-field")
            {
                if (parts.Length < 3)
                {
                    throw new InvalidOperationException("patch-field requires field and value");
                }
                ApplyFieldPatch(mainForm, parts[1], parts[2]);
                continue;
            }
            if (op == "patch-event")
            {
                if (parts.Length < 3)
                {
                    throw new InvalidOperationException("patch-event requires event and lines");
                }
                ApplyEventPatch(mainForm, parts[1], parts[2].Split(new string[] { "\\n" }, StringSplitOptions.None));
                continue;
            }
            if (op == "save")
            {
                PersistProject(mainForm);
                continue;
            }
            if (op == "dump-page")
            {
                bool dumped = DumpCurrentPage(mainForm);
                Trace("macro DumpCurrentPage() returned " + dumped);
                if (!dumped)
                {
                    throw new InvalidOperationException("DumpCurrentPage() returned false");
                }
                continue;
            }
            if (op == "compile")
            {
                if (parts.Length < 2)
                {
                    throw new InvalidOperationException("compile requires output path");
                }
                compileOutputPath = parts[1];
                managedCompileOk = RunManagedCompile(mainForm, compileOutputPath);
                Trace("macro RunManagedCompile() returned " + managedCompileOk + " bytes=" + managedCompileBytes);
                continue;
            }
            throw new InvalidOperationException("Unsupported macro op: " + op);
        }
        CaptureState(mainForm);
    }

    private static void SelectObject(Form mainForm, int index)
    {
        object tftEdit = GetField(mainForm, "TFTEDIT0");
        Trace("macro selecting objectIndex=" + index);
        InvokeMethod(tftEdit, "setxuanzhong_del", new object[] { 0 });
        InvokeMethod(tftEdit, "setxuanzhong_add", new object[] { index });
        InvokeMethod(mainForm, "objselect", null);
        Application.DoEvents();
    }

    private static int AddPage(Form mainForm, string pageName)
    {
        if (string.IsNullOrEmpty(pageName))
        {
            throw new InvalidOperationException("add page name is empty");
        }
        object myapp = GetField(mainForm, "Myapp");
        if (myapp == null)
        {
            throw new InvalidOperationException("Myapp is null while adding page");
        }
        object resourcesPages = GetField(myapp, "ResourcesPages");
        IList list = resourcesPages as IList;
        if (list == null)
        {
            throw new InvalidOperationException("Myapp.ResourcesPages is not IList");
        }
        resourcesPageCountBeforeAdd = list.Count;

        Type resourcePageType = FindType("hmitype.ResourcesPage");
        Type resourceFileType = FindType("hmitype.ResourcesFile");
        object resourcePage = Activator.CreateInstance(resourcePageType);
        object resourceFile = Activator.CreateInstance(resourceFileType);
        SetField(resourceFile, "FileName", "");
        SetField(resourceFile, "ResourcesType", GetStaticField("hmitype.ResourcesType", "page"));

        Trace("invoking Myapp.Creatnewpage(true) for add-page " + pageName + " beforeCount=" + resourcesPageCountBeforeAdd);
        object newPage = InvokeMethod(myapp, "Creatnewpage", new object[] { true });
        if (newPage == null)
        {
            throw new InvalidOperationException("Creatnewpage(true) returned null");
        }
        SetPageName(newPage, pageName);

        SetField(resourcePage, "file", resourceFile);
        SetField(resourcePage, "page", newPage);
        list.Add(resourcePage);
        InvokeMethod(myapp, "RefpageID", null);
        int newIndex = list.Count - 1;
        resourcesPageCountAfterAdd = list.Count;
        pageIndex = newIndex;
        object addedResourcePage = list[newIndex];
        object addedPage = GetFieldOrProperty(addedResourcePage, "page");
        if (addedPage != null)
        {
            newPage = addedPage;
        }
        InvokeMethod(newPage, "SetPageChanegState", new object[] { 1 });

        object pageAdmin = GetField(mainForm, "pageadmin1");
        InvokeMethod(pageAdmin, "RefList", null);
        InvokeMethod(pageAdmin, "selectindex", new object[] { newIndex });
        SetField(mainForm, "dpage", newPage);
        InvokeMethod(mainForm, "RefPage", null);
        Application.DoEvents();
        WaitForCondition(new ConditionDelegate(IsRequestedPageReady), mainForm, 10.0, "add-page selection");
        Trace("add-page selected index=" + newIndex + " afterCount=" + resourcesPageCountAfterAdd);
        return newIndex;
    }

    private static void SetPageName(object page, string pageName)
    {
        object pageData = GetField(page, "pagedata");
        if (pageData == null)
        {
            throw new InvalidOperationException("page.pagedata is null");
        }
        SetField(pageData, "pagename", pageName);
        SetField(page, "pagedata", pageData);

        object objs = GetField(page, "objs");
        IList objList = objs as IList;
        if (objList == null || objList.Count == 0)
        {
            return;
        }
        object pageObject = objList[0];
        try
        {
            bool ok = (bool)InvokeMethod(pageObject, "Setattstr", new object[] { "objname", pageName, false });
            Trace("Setattstr(page.objname," + pageName + ",false) => " + ok);
        }
        catch (Exception ex)
        {
            Trace("Setattstr page objname failed: " + FlattenException(ex));
        }
    }

    private static bool IsObjectCountIncreased(Form mainForm)
    {
        object dpage = GetField(mainForm, "dpage");
        int count = ReadPageObjectCount(dpage);
        return count > createBeforeObjectCount;
    }

    private static void EnsureVpAddressSpace(Form mainForm)
    {
        if (string.IsNullOrEmpty(createControlVarName) || createControlVarName.IndexOf("VP", StringComparison.OrdinalIgnoreCase) < 0)
        {
            return;
        }
        object myapp = GetField(mainForm, "Myapp");
        object dpage = GetField(mainForm, "dpage");
        if (myapp == null || dpage == null)
        {
            return;
        }
        string currentRanges = SafeString(InvokeMethod(myapp, "APPMEDATA_Getstring", null));
        if (string.IsNullOrEmpty(currentRanges))
        {
            bool setRanges = (bool)InvokeMethod(myapp, "APPMEDATA_Setstring", new object[] { "1000-17FF" });
            Trace("APPMEDATA_Setstring(1000-17FF) => " + setRanges);
            if (!setRanges)
            {
                throw new InvalidOperationException("APPMEDATA_Setstring(1000-17FF) failed");
            }
            currentRanges = "1000-17FF";
        }
        EnsureRam1Open(myapp);
        string vpValue = ReadFieldString(mainForm, "VP");
        if (vpValue == null || vpValue.Length == 0)
        {
            Trace("VP field not present for control " + createControlVarName);
            return;
        }
        if (vpValue == "65535")
        {
            int defaultVp = ParseFirstAppMedataStart(currentRanges);
            bool ok = (bool)InvokeMethod(dpage, "changobjattch", new object[] { objectIndex, "VP", defaultVp.ToString() });
            Trace("changobjattch(" + objectIndex + ",VP," + defaultVp + ") => " + ok);
            if (!ok)
            {
                throw new InvalidOperationException("changobjattch failed for field VP");
            }
        }
    }

    private static void EnsureRam1Open(object myapp)
    {
        object appdata = GetField(myapp, "appdata");
        if (appdata == null)
        {
            return;
        }
        FieldInfo ram1Field = appdata.GetType().GetField("RAM1_OPEN", BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (ram1Field == null)
        {
            return;
        }
        object current = ram1Field.GetValue(appdata);
        int currentValue = current == null ? 0 : Convert.ToInt32(current);
        if (currentValue == 1)
        {
            return;
        }
        ram1Field.SetValue(appdata, (byte)1);
        SetField(myapp, "appdata", appdata);
        Trace("set appdata.RAM1_OPEN=1");
    }

    private static int ParseFirstAppMedataStart(string ranges)
    {
        string[] lines = ranges.Replace("\r\n", "\n").Split(new char[] { '\n' }, StringSplitOptions.RemoveEmptyEntries);
        if (lines.Length == 0)
        {
            return 4096;
        }
        string[] parts = lines[0].Split('-');
        if (parts.Length != 2)
        {
            return 4096;
        }
        return Convert.ToInt32(parts[0], 16);
    }

    private static bool ParseBoolArg(string value)
    {
        if (value == null)
        {
            return false;
        }
        string normalized = value.Trim().ToLowerInvariant();
        return normalized == "1" || normalized == "true" || normalized == "yes" || normalized == "on";
    }

    private static bool RunManagedCompile(Form mainForm, string outputTftPath)
    {
        object myapp = GetField(mainForm, "Myapp");
        if (myapp == null)
        {
            return false;
        }
        object compileModeType = FindType("hmitype.CompileMode");
        object outputMode = Enum.Parse((Type)compileModeType, "OutPutTFT");
        Type appbianyiType = FindType("hmitype.appbianyi");
        MethodInfo fileBianyi = appbianyiType.GetMethod("FileBianyi", BindingFlags.Public | BindingFlags.Static);
        if (fileBianyi == null)
        {
            throw new MissingMethodException("hmitype.appbianyi", "FileBianyi");
        }
        RichTextBox log = new RichTextBox();
        StartCreateModalCloseTimer();
        try
        {
            bool ok = (bool)fileBianyi.Invoke(null, new object[] { myapp, outputTftPath, log, outputMode });
            managedCompileText = log.Text;
            if (File.Exists(outputTftPath))
            {
                managedCompileBytes = new FileInfo(outputTftPath).Length;
            }
            return ok;
        }
        finally
        {
            StopCreateModalCloseTimer();
            log.Dispose();
        }
    }

    private static bool DumpCurrentPage(Form mainForm)
    {
        object myapp = GetField(mainForm, "Myapp");
        object dpage = GetField(mainForm, "dpage");
        if (myapp == null || dpage == null)
        {
            return false;
        }
        if (File.Exists(pageDumpPath))
        {
            try
            {
                File.Delete(pageDumpPath);
            }
            catch
            {
            }
        }
        Trace("invoking OutPutPageFile => " + pageDumpPath);
        bool dumped = (bool)InvokeMethod(
            myapp,
            "OutPutPageFile",
            new object[] { dpage, null, pageDumpPath, false });
        return dumped && File.Exists(pageDumpPath);
    }

    private static int ResolveRuntimePageIndex(Form mainForm, string requestedPageResource, int fallbackIndex)
    {
        if (string.IsNullOrEmpty(requestedPageResource))
        {
            return fallbackIndex;
        }
        object myapp = GetField(mainForm, "Myapp");
        object resourcesPages = GetField(myapp, "ResourcesPages");
        IList list = resourcesPages as IList;
        if (list == null)
        {
            return fallbackIndex;
        }
        int i;
        for (i = 0; i < list.Count; i++)
        {
            object resourcePage = list[i];
            object fileInfo = GetFieldOrProperty(resourcePage, "file");
            string fileName = SafeString(GetFieldOrProperty(fileInfo, "FileName"));
            if (fileName == requestedPageResource)
            {
                Trace("resolved runtime page index " + i + " for page resource " + requestedPageResource);
                return i;
            }
        }
        Trace("falling back to requested page index " + fallbackIndex + " for page resource " + requestedPageResource);
        return fallbackIndex;
    }

    private static void CloseBlockingForms(bool includeMessages, bool includeProgressForms, bool startupPhase)
    {
        int i;
        for (i = Application.OpenForms.Count - 1; i >= 0; i--)
        {
            Form form = Application.OpenForms[i];
            if (form == null)
            {
                continue;
            }
            string fullName = form.GetType().FullName ?? "";
            string name = form.Name ?? "";
            string text = form.Text ?? "";
            bool canCloseStartupTransient =
                !startupPhase
                || DateTime.UtcNow >= startupDialogCloseAllowedUtc
                || IsImmediateStartupCloseCandidate(form, fullName, name, text);
            bool shouldClose =
                (
                    canCloseStartupTransient
                    && (
                        fullName == "HMIFORM.logon"
                        || name == "logon"
                        || fullName == "hmitype.webform"
                        || name == "webform"
                    )
                )
                || (
                    includeProgressForms
                    && (
                        fullName == "hmitype.AppResourcesmakeFrom"
                        || name == "AppResourcesmakeFrom"
                        || text == "progform"
                    )
                );
            if (
                includeMessages
                && canCloseStartupTransient
                && (
                    fullName == "hmitype.MessageForm"
                    || fullName == "hmioldapp.MessageForm"
                    || name == "MessageForm"
                    || text == "MessageForm"
                )
            )
            {
                shouldClose = true;
                try
                {
                    form.DialogResult = DialogResult.OK;
                }
                catch
                {
                }
            }
            if (shouldClose)
            {
                Trace("closing blocking form " + DescribeForm(form));
                try
                {
                    form.Close();
                }
                catch
                {
                }
            }
        }
        Application.DoEvents();
    }

    private static void StartCreateModalCloseTimer()
    {
        StopCreateModalCloseTimer();
        createModalCloseTimer = new Timer();
        createModalCloseTimer.Interval = 100;
        createModalCloseTimer.Tick += new EventHandler(CreateModalCloseTimer_Tick);
        createModalCloseTimer.Start();
        Trace("create modal close timer started");
    }

    private static void StopCreateModalCloseTimer()
    {
        if (createModalCloseTimer != null)
        {
            createModalCloseTimer.Stop();
            createModalCloseTimer.Dispose();
            createModalCloseTimer = null;
            Trace("create modal close timer stopped");
        }
    }

    private static void CreateModalCloseTimer_Tick(object sender, EventArgs e)
    {
        try
        {
            int i;
            for (i = Application.OpenForms.Count - 1; i >= 0; i--)
            {
                Form form = Application.OpenForms[i];
                if (form == null)
                {
                    continue;
                }
                string fullName = form.GetType().FullName ?? "";
                string name = form.Name ?? "";
                string text = form.Text ?? "";
                if (
                    fullName == "hmitype.AppResourcesmakeFrom"
                    || name == "AppResourcesmakeFrom"
                    || text == "progform"
                    || fullName == "hmitype.webform"
                    || name == "webform"
                    || fullName == "hmitype.MessageForm"
                    || fullName == "hmioldapp.MessageForm"
                    || name == "MessageForm"
                    || text == "MessageForm"
                )
                {
                    Trace("auto-closing create modal " + DescribeForm(form));
                    try
                    {
                        form.DialogResult = DialogResult.OK;
                    }
                    catch
                    {
                    }
                    try
                    {
                        form.Close();
                    }
                    catch
                    {
                    }
                }
            }
            Application.DoEvents();
        }
        catch
        {
        }
    }

    private static string DescribeForm(Form form)
    {
        if (form == null)
        {
            return "<null>";
        }
        string fullName = form.GetType().FullName ?? "";
        string text = form.Text ?? "";
        string body = TryGetFormBody(form);
        if (body.Length > 120)
        {
            body = body.Substring(0, 120);
        }
        return fullName + " text=" + text + " body=" + body.Replace("\r", "\\r").Replace("\n", "\\n");
    }

    private static bool IsImmediateStartupCloseCandidate(Form form, string fullName, string name, string text)
    {
        if (form == null)
        {
            return false;
        }
        if (fullName == "hmitype.download" || string.Equals(text, "Update", StringComparison.OrdinalIgnoreCase))
        {
            return true;
        }
        if (
            fullName == "hmitype.MessageForm"
            || fullName == "hmioldapp.MessageForm"
            || name == "MessageForm"
            || text == "MessageForm"
        )
        {
            string body = TryGetFormBody(form);
            if (body.IndexOf("Version mismatch", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return true;
            }
            if (body.IndexOf("内存读写定制版", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return true;
            }
            if (body.IndexOf("支持内存读写的软件打开", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return true;
            }
            if (body.IndexOf("暴力篡改", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return true;
            }
            if (body.IndexOf("版权声明", StringComparison.OrdinalIgnoreCase) >= 0)
            {
                return true;
            }
        }
        return false;
    }

    private static string TryGetFormBody(Form form)
    {
        string body = "";
        try
        {
            object richText = GetFieldOrProperty(form, "textmessage");
            TextBoxBase textBox = richText as TextBoxBase;
            if (textBox != null)
            {
                body = textBox.Text ?? "";
            }
            if (body.Length == 0)
            {
                object label = GetFieldOrProperty(form, "label1");
                Control labelControl = label as Control;
                if (labelControl != null)
                {
                    body = labelControl.Text ?? "";
                }
            }
        }
        catch
        {
        }
        return body;
    }

    private static bool IsProjectLoaded(Form mainForm)
    {
        object myapp = GetField(mainForm, "Myapp");
        return myapp != null;
    }

    private static bool IsMainPageReady(Form mainForm)
    {
        object myapp = GetField(mainForm, "Myapp");
        object dpage = GetField(mainForm, "dpage");
        return myapp != null && dpage != null;
    }

    private static bool IsRequestedPageReady(Form mainForm)
    {
        object dpage = GetField(mainForm, "dpage");
        if (dpage == null)
        {
            return false;
        }
        int currentPageId = ReadCurrentPageId(dpage);
        return currentPageId == pageIndex;
    }

    private static void WaitForCondition(ConditionDelegate condition, Form mainForm, double timeoutSeconds, string label)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline)
        {
            if (condition(mainForm))
            {
                return;
            }
            CloseBlockingForms(true, true, false);
            Application.DoEvents();
            System.Threading.Thread.Sleep(20);
        }
        Trace("timeout waiting for " + label);
        TraceFormsSnapshot();
        throw new InvalidOperationException("Timed out waiting for " + label);
    }

    private static bool TryWaitForCondition(ConditionDelegate condition, Form mainForm, double timeoutSeconds)
    {
        DateTime deadline = DateTime.UtcNow.AddSeconds(timeoutSeconds);
        while (DateTime.UtcNow < deadline)
        {
            if (condition(mainForm))
            {
                return true;
            }
            CloseBlockingForms(true, true, false);
            Application.DoEvents();
            System.Threading.Thread.Sleep(20);
        }
        Trace("condition not ready after " + timeoutSeconds.ToString("0.0") + "s");
        TraceFormsSnapshot();
        return false;
    }

    private static void CaptureState(Form mainForm)
    {
        object dpage = GetField(mainForm, "dpage");
        if (dpage != null)
        {
            object pageData = GetField(dpage, "pagedata");
            openedPageName = SafeString(GetField(pageData, "pagename"));
            openedPageId = ReadCurrentPageId(dpage);
        }

        object tftEdit = GetField(mainForm, "TFTEDIT0");
        object selectObjedits = GetField(tftEdit, "selectobjedits");
        IList selectedList = selectObjedits as IList;
        if (selectedList != null && selectedList.Count > 0)
        {
            object firstEdit = selectedList[0];
            object dobj = GetField(firstEdit, "dobj");
            canvasSelectedObjname = SafeString(GetFieldOrProperty(dobj, "objname"));
        }

        object objatt2 = GetField(mainForm, "objatt2");
        object objs = GetField(objatt2, "objs");
        IList objList = objs as IList;
        if (objList != null && objList.Count > 0)
        {
            attributeSelectedObjname = SafeString(GetFieldOrProperty(objList[0], "objname"));
        }

        ComboBox comboBox = GetField(objatt2, "comboBox1") as ComboBox;
        if (comboBox != null)
        {
            comboSelectedText = comboBox.Text;
        }

        DataGridView grid = GetField(objatt2, "dataGridView1") as DataGridView;
        if (grid != null)
        {
            propertyGridRowCount = grid.Rows.Count;
            foreach (DataGridViewRow row in grid.Rows)
            {
                object nameCell = row.Cells["name"].Value;
                if (SafeString(nameCell) == "objname")
                {
                    gridObjnameValue = SafeString(row.Cells["val"].Value);
                    break;
                }
            }
        }
        object myapp = GetField(mainForm, "Myapp");
        if (myapp != null)
        {
            object resourcesPages = GetField(myapp, "ResourcesPages");
            IList resourcePageList = resourcesPages as IList;
            resourcesPageCount = resourcePageList == null ? -1 : resourcePageList.Count;
            resourcesPageNames = ReadResourcesPageNames(resourcePageList);
            appMedataString = SafeString(InvokeMethod(myapp, "APPMEDATA_Getstring", null));
            object appdata = GetField(myapp, "appdata");
            if (appdata != null)
            {
                ram1Open = Convert.ToInt32(GetField(appdata, "RAM1_OPEN"));
                appMedataHex = ReadAppMedataHex(appdata);
            }
        }
    }

    private static void ApplyPatchSpec(Form mainForm)
    {
        string[] lines = File.ReadAllLines(patchSpecPath, Encoding.UTF8);
        int i;
        for (i = 0; i < lines.Length; i++)
        {
            string line = lines[i].Trim();
            if (line.Length == 0 || line.StartsWith("#"))
            {
                continue;
            }
            string[] parts = line.Split(new char[] { '\t' });
            if (parts.Length < 3)
            {
                throw new InvalidOperationException("Unsupported patch spec line: " + line);
            }
            if (parts[0] == "field")
            {
                ApplyFieldPatch(mainForm, parts[1], parts[2]);
                continue;
            }
            if (parts[0] == "event")
            {
                ApplyEventPatch(mainForm, parts[1], parts[2].Split(new string[] { "\\n" }, StringSplitOptions.None));
                continue;
            }
            throw new InvalidOperationException("Unsupported patch spec line: " + line);
        }
    }

    private static void ApplyFieldPatch(Form mainForm, string fieldName, string value)
    {
        object dpage = GetField(mainForm, "dpage");
        if (dpage == null)
        {
            throw new InvalidOperationException("dpage is null while applying patch " + fieldName);
        }
        bool ok = (bool)InvokeMethod(dpage, "changobjattch", new object[] { objectIndex, fieldName, value });
        Trace("changobjattch(" + objectIndex + "," + fieldName + "," + value + ") => " + ok);
        if (!ok)
        {
            object objs = GetField(dpage, "objs");
            IList list = objs as IList;
            if (list != null && objectIndex >= 0 && objectIndex < list.Count)
            {
                object obj = list[objectIndex];
                object forcedAtt = InvokeMethod(obj, "Getatt", new object[] { fieldName, true });
                Trace("Getatt(" + fieldName + ",true) => " + (forcedAtt == null ? "<null>" : forcedAtt.GetType().FullName));
                if (forcedAtt != null)
                {
                    object upatt = GetField(forcedAtt, "Upatt0");
                    if (upatt != null)
                    {
                        Trace(
                            "forced field meta name=" + fieldName
                            + " attlei=" + SafeString(GetFieldOrProperty(upatt, "attlei"))
                            + " merrylenth=" + SafeString(GetFieldOrProperty(upatt, "merrylenth"))
                            + " min=" + SafeString(GetFieldOrProperty(upatt, "minval"))
                            + " max=" + SafeString(GetFieldOrProperty(upatt, "maxval"))
                        );
                    }
                }
                bool forcedOk = (bool)InvokeMethod(obj, "Setattstr", new object[] { fieldName, value, true });
                Trace("Setattstr(" + fieldName + "," + value + ",true) => " + forcedOk);
                ok = forcedOk;
            }
        }
        if (!ok)
        {
            throw new InvalidOperationException("changobjattch failed for field " + fieldName);
        }
    }

    private static void ApplyEventPatch(Form mainForm, string eventName, string[] lines)
    {
        object objatt1 = GetField(mainForm, "objatt1");
        if (objatt1 == null)
        {
            throw new InvalidOperationException("objatt1 is null while applying event patch");
        }
        string eventLabel = ResolveEventLabel(eventName);
        Trace("ApplyEventPatch event=" + eventName + " label=" + eventLabel);
        InvokeMethod(objatt1, "setxuanzhong", new object[] { eventLabel, 0, 0 });
        Application.DoEvents();
        InvokeMethod(objatt1, "attload", new object[] { eventLabel });
        object textBox1 = GetField(objatt1, "textBox1");
        SetProperty(textBox1, "Text", JoinEventLines(lines));
        SetField(objatt1, "ischange", true);
        InvokeMethod(objatt1, "SaveCodes", null);
    }

    private static string ReadFieldString(Form mainForm, string fieldName)
    {
        object dpage = GetField(mainForm, "dpage");
        if (dpage == null)
        {
            return null;
        }
        object objs = GetField(dpage, "objs");
        IList list = objs as IList;
        if (list == null || objectIndex < 0 || objectIndex >= list.Count)
        {
            return null;
        }
        object obj = list[objectIndex];
        object value = InvokeMethod(obj, "GetattVal_string", new object[] { fieldName, true });
        return SafeString(value);
    }

    private static string ResolveEventLabel(string eventName)
    {
        object appevents = GetStaticField("hmitype.AppData", "appevents");
        if (appevents == null)
        {
            throw new InvalidOperationException("hmitype.AppData.appevents is null");
        }
        object eventInfo = GetField(appevents, eventName);
        if (eventInfo == null && !string.IsNullOrEmpty(eventName))
        {
            System.Reflection.FieldInfo[] fields = appevents.GetType().GetFields(BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
            int i;
            for (i = 0; i < fields.Length; i++)
            {
                System.Reflection.FieldInfo field = fields[i];
                if (field == null)
                {
                    continue;
                }
                if (string.Equals(field.Name, eventName, StringComparison.OrdinalIgnoreCase))
                {
                    eventInfo = field.GetValue(appevents);
                    break;
                }
            }
        }
        if (eventInfo == null)
        {
            throw new InvalidOperationException("Unknown official event name: " + eventName);
        }
        string label = SafeString(GetFieldOrProperty(eventInfo, "label"));
        if (string.IsNullOrEmpty(label))
        {
            throw new InvalidOperationException("Official event label is empty for " + eventName);
        }
        return label;
    }

    private static string JoinEventLines(string[] lines)
    {
        if (lines == null || lines.Length == 0)
        {
            return "";
        }
        return string.Join("\r\n", lines) + "\r\n";
    }

    private static string ReadAppMedataHex(object appdata)
    {
        StringBuilder builder = new StringBuilder();
        int i;
        for (i = 0; i < 6; i++)
        {
            object raw = GetField(appdata, "APPMEDATAHEX" + i);
            uint value = raw == null ? 0u : Convert.ToUInt32(raw);
            byte[] bytes = BitConverter.GetBytes(value);
            int j;
            for (j = 0; j < bytes.Length; j++)
            {
                builder.Append(bytes[j].ToString("x2"));
            }
        }
        return builder.ToString();
    }

    private static void BootstrapOfficialRuntime()
    {
        string appDataDir = Path.Combine(
            Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData),
            "USART HMI");
        SetDllDirectory(appDataDir);
        Directory.SetCurrentDirectory(installDir);

        Assembly wrapper = Assembly.LoadFile(Path.Combine(installDir, "USART HMI.exe"));
        Assembly appRun = Assembly.LoadFile(Path.Combine(appDataDir, "ApplicationRUN.s0"));

        Type resourcesType = wrapper.GetType("USARTHMI.Properties.Resources", true);
        PropertyInfo resourceManagerProperty = resourcesType.GetProperty(
            "ResourceManager",
            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        object resourceManager = resourceManagerProperty.GetValue(null, null);

        Type appRunType = appRun.GetType("ApplicationRUN.ApplicationRunMain", true);
        MethodInfo myInit = appRunType.GetMethod("MyInit", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        object result = myInit.Invoke(null, new object[] { resourceManager, Path.Combine(installDir, "ACTR.dll") });
        int initCode = Convert.ToInt32(result);
        if (initCode != 0)
        {
            throw new InvalidOperationException("ApplicationRUN.ApplicationRunMain.MyInit failed: " + initCode);
        }
    }

    private static void InvokeHmiformRunMain()
    {
        Type hmiformProgram = FindType("HMIFORM.Program");
        MethodInfo runMain = hmiformProgram.GetMethod("RunMain", BindingFlags.Public | BindingFlags.Static);
        if (runMain == null)
        {
            throw new MissingMethodException("HMIFORM.Program", "RunMain");
        }
        runMain.Invoke(null, null);
    }

    private static Type FindType(string fullName)
    {
        Type type = null;
        foreach (Assembly assembly in AppDomain.CurrentDomain.GetAssemblies())
        {
            type = assembly.GetType(fullName, false);
            if (type != null)
            {
                return type;
            }
        }

        string actrPath = Path.Combine(installDir, "ACTR.dll");
        if (File.Exists(actrPath))
        {
            Assembly actr = Assembly.LoadFile(actrPath);
            type = actr.GetType(fullName, false);
            if (type != null)
            {
                return type;
            }
        }

        throw new TypeLoadException(fullName);
    }

    private static Form FindMainForm()
    {
        foreach (Form form in Application.OpenForms)
        {
            if (form != null && form.GetType().FullName == "HMIFORM.main")
            {
                return form;
            }
        }
        return null;
    }

    private static void BeginClose(Form mainForm)
    {
        if (mainForm == null || mainForm.IsDisposed)
        {
            Trace("Application.ExitThread without HMIFORM.main");
            Application.ExitThread();
            return;
        }
        mainForm.BeginInvoke(new MethodInvoker(CloseMainWindow));
    }

    private static void CloseMainWindow()
    {
        Form mainForm = FindMainForm();
        if (mainForm != null && !mainForm.IsDisposed)
        {
            Trace("closing HMIFORM.main");
            mainForm.Close();
        }
        Trace("Application.ExitThread");
        Application.ExitThread();
    }

    private static int ReadCurrentPageId(object dpage)
    {
        object pageData = GetField(dpage, "pagedata");
        object pageId = GetField(pageData, "pageid");
        return pageId == null ? -1 : Convert.ToInt32(pageId);
    }

    private static int ReadPageObjectCount(object dpage)
    {
        object objs = GetField(dpage, "objs");
        IList list = objs as IList;
        return list == null ? 0 : list.Count;
    }

    private static int ReadCurrentSelectedObjectIndex(Form mainForm)
    {
        object tftEdit = GetField(mainForm, "TFTEDIT0");
        object selectObjedits = GetField(tftEdit, "selectobjedits");
        IList selectedList = selectObjedits as IList;
        if (selectedList == null || selectedList.Count == 0)
        {
            return -1;
        }
        object firstEdit = selectedList[0];
        object dobj = GetField(firstEdit, "dobj");
        object objDataRam = GetField(dobj, "objdataram");
        object idValue = GetField(objDataRam, "id");
        return idValue == null ? -1 : Convert.ToInt32(idValue);
    }

    private static object GetField(object instance, string fieldName)
    {
        if (instance == null)
        {
            return null;
        }
        Type type = instance.GetType();
        FieldInfo field = type.GetField(fieldName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        return field == null ? null : field.GetValue(instance);
    }

    private static object GetStaticField(string typeName, string fieldName)
    {
        Type type = FindType(typeName);
        FieldInfo field = type.GetField(fieldName, BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic);
        return field == null ? null : field.GetValue(null);
    }

    private static object GetFieldOrProperty(object instance, string name)
    {
        if (instance == null)
        {
            return null;
        }
        FieldInfo field = instance.GetType().GetField(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (field != null)
        {
            return field.GetValue(instance);
        }
        PropertyInfo property = instance.GetType().GetProperty(name, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (property != null)
        {
            return property.GetValue(instance, null);
        }
        return null;
    }

    private static void SetField(object instance, string fieldName, object value)
    {
        if (instance == null)
        {
            throw new InvalidOperationException("Cannot set " + fieldName + " on a null instance");
        }
        FieldInfo field = instance.GetType().GetField(fieldName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (field == null)
        {
            throw new MissingFieldException(instance.GetType().FullName, fieldName);
        }
        field.SetValue(instance, value);
    }

    private static void SetProperty(object instance, string propertyName, object value)
    {
        if (instance == null)
        {
            throw new InvalidOperationException("Cannot set " + propertyName + " on a null instance");
        }
        PropertyInfo property = instance.GetType().GetProperty(propertyName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        if (property == null)
        {
            throw new MissingMemberException(instance.GetType().FullName, propertyName);
        }
        property.SetValue(instance, value, null);
    }

    private static object InvokeMethod(object instance, string methodName, object[] args)
    {
        if (instance == null)
        {
            throw new InvalidOperationException("Cannot invoke " + methodName + " on a null instance");
        }
        Type type = instance.GetType();
        if (args == null)
        {
            args = new object[0];
        }
        Type[] parameterTypes = null;
        if (args.Length > 0)
        {
            parameterTypes = new Type[args.Length];
            int i;
            for (i = 0; i < args.Length; i++)
            {
                parameterTypes[i] = args[i] == null ? typeof(object) : args[i].GetType();
            }
        }
        MethodInfo method;
        if (parameterTypes == null)
        {
            method = type.GetMethod(
                methodName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null,
                Type.EmptyTypes,
                null);
        }
        else
        {
            method = type.GetMethod(
                methodName,
                BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic,
                null,
                parameterTypes,
                null);
        }
        if (method == null)
        {
            method = type.GetMethod(methodName, BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic);
        }
        if (method == null)
        {
            throw new MissingMethodException(type.FullName, methodName);
        }
        return method.Invoke(instance, args);
    }

    private static void StopTimer()
    {
        if (pollTimer != null)
        {
            pollTimer.Stop();
            pollTimer.Dispose();
            pollTimer = null;
        }
    }

    private static void WriteReport()
    {
        try
        {
            string directory = Path.GetDirectoryName(reportPath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }
            Trace("writing report");
            Form currentMainForm = FindMainForm();
            List<string> visibleFieldNames = ReadObjectFieldNames(currentMainForm, false);
            List<string> allFieldNames = ReadObjectFieldNames(currentMainForm, true);
            StringBuilder builder = new StringBuilder();
            builder.Append("{\n");
            AppendJson(builder, "status", failureMessage == null ? "ok" : "failed", true);
            AppendJson(builder, "hmi_path", hmiPath, true);
            AppendJson(builder, "install_dir", installDir, true);
            AppendJson(builder, "page_index", pageIndex, false);
            builder.Append(",\n");
            AppendJson(builder, "object_index", objectIndex, false);
            builder.Append(",\n");
            AppendJson(builder, "add_page_name", addPageName, true);
            AppendJson(builder, "macro_action_count", macroActionCount, true);
            AppendJson(builder, "resources_page_count", resourcesPageCount, true);
            AppendJsonArray(builder, "resources_page_names", resourcesPageNames, true);
            AppendJson(builder, "resources_page_count_before_add", resourcesPageCountBeforeAdd, true);
            AppendJson(builder, "resources_page_count_after_add", resourcesPageCountAfterAdd, false);
            builder.Append(",\n");
            AppendJson(builder, "opened_page_name", openedPageName, true);
            AppendJson(builder, "opened_page_id", openedPageId, false);
            builder.Append(",\n");
            AppendJson(builder, "canvas_selected_objname", canvasSelectedObjname, true);
            AppendJson(builder, "attribute_selected_objname", attributeSelectedObjname, true);
            AppendJson(builder, "grid_objname_value", gridObjnameValue, true);
            AppendJson(builder, "property_grid_row_count", propertyGridRowCount, false);
            builder.Append(",\n");
            AppendJsonArray(builder, "visible_field_names", visibleFieldNames, true);
            AppendJsonArray(builder, "all_field_names", allFieldNames, false);
            builder.Append(",\n");
            AppendJson(builder, "combo_selected_text", comboSelectedText, true);
            AppendJson(builder, "appmedata_string", appMedataString, true);
            AppendJson(builder, "appmedata_hex", appMedataHex, true);
            AppendJson(builder, "ram1_open", ram1Open, false);
            builder.Append(",\n");
            AppendJson(builder, "saved_project", savedProjectOk ? 1 : 0, false);
            builder.Append(",\n");
            AppendJson(builder, "managed_compile_ok", managedCompileOk ? 1 : 0, false);
            builder.Append(",\n");
            AppendJson(builder, "managed_compile_text", managedCompileText, true);
            AppendJson(builder, "managed_compile_output", compileOutputPath, true);
            AppendJson(builder, "managed_compile_bytes", (int)managedCompileBytes, false);
            builder.Append(",\n");
            AppendJson(builder, "error", failureMessage, false);
            builder.Append("}\n");
            File.WriteAllText(reportPath, builder.ToString(), Encoding.UTF8);
        }
        catch
        {
        }
    }

    private static void AppendJson(StringBuilder builder, string name, string value, bool withComma)
    {
        builder.Append("  \"");
        builder.Append(JsonEscape(name));
        builder.Append("\": ");
        if (value == null)
        {
            builder.Append("null");
        }
        else
        {
            builder.Append("\"");
            builder.Append(JsonEscape(value));
            builder.Append("\"");
        }
        if (withComma)
        {
            builder.Append(",\n");
        }
    }

    private static void AppendJson(StringBuilder builder, string name, int value, bool withComma)
    {
        builder.Append("  \"");
        builder.Append(JsonEscape(name));
        builder.Append("\": ");
        builder.Append(value.ToString());
        if (withComma)
        {
            builder.Append(",\n");
        }
    }

    private static void AppendJsonArray(StringBuilder builder, string name, List<string> values, bool withComma)
    {
        builder.Append("  \"");
        builder.Append(JsonEscape(name));
        builder.Append("\": ");
        if (values == null)
        {
            builder.Append("null");
        }
        else
        {
            builder.Append("[");
            int i;
            for (i = 0; i < values.Count; i++)
            {
                if (i > 0)
                {
                    builder.Append(", ");
                }
                builder.Append("\"");
                builder.Append(JsonEscape(values[i] ?? ""));
                builder.Append("\"");
            }
            builder.Append("]");
        }
        if (withComma)
        {
            builder.Append(",\n");
        }
    }

    private static List<string> ReadObjectFieldNames(Form mainForm, bool includeForced)
    {
        List<string> names = new List<string>();
        if (mainForm == null)
        {
            return names;
        }
        object dpage = GetField(mainForm, "dpage");
        if (dpage == null)
        {
            return names;
        }
        object objs = GetField(dpage, "objs");
        IList list = objs as IList;
        if (list == null || objectIndex < 0 || objectIndex >= list.Count)
        {
            return names;
        }
        object obj = list[objectIndex];
        object atts = GetField(obj, "atts");
        IList attList = atts as IList;
        if (attList == null)
        {
            return names;
        }
        int i;
        for (i = 0; i < attList.Count; i++)
        {
            object att = attList[i];
            string attname = SafeString(GetFieldOrProperty(att, "attname"));
            if (string.IsNullOrEmpty(attname))
            {
                continue;
            }
            bool include = includeForced;
            if (!includeForced)
            {
                try
                {
                    include = Convert.ToBoolean(InvokeMethod(obj, "checkatt", new object[] { att }));
                }
                catch
                {
                    include = false;
                }
            }
            if (include && !names.Contains(attname))
            {
                names.Add(attname);
            }
        }
        return names;
    }

    private static List<string> ReadResourcesPageNames(IList resourcePageList)
    {
        List<string> names = new List<string>();
        if (resourcePageList == null)
        {
            return names;
        }
        int i;
        for (i = 0; i < resourcePageList.Count; i++)
        {
            object resourcePage = resourcePageList[i];
            object page = GetFieldOrProperty(resourcePage, "page");
            object pageData = GetField(page, "pagedata");
            string pageName = SafeString(GetField(pageData, "pagename"));
            object file = GetFieldOrProperty(resourcePage, "file");
            string fileName = SafeString(GetFieldOrProperty(file, "FileName"));
            names.Add((pageName ?? "") + "|" + (fileName ?? ""));
        }
        return names;
    }

    private static string JsonEscape(string value)
    {
        if (value == null)
        {
            return "";
        }
        StringBuilder builder = new StringBuilder();
        int i;
        for (i = 0; i < value.Length; i++)
        {
            char ch = value[i];
            switch (ch)
            {
                case '\\':
                    builder.Append("\\\\");
                    break;
                case '"':
                    builder.Append("\\\"");
                    break;
                case '\r':
                    builder.Append("\\r");
                    break;
                case '\n':
                    builder.Append("\\n");
                    break;
                case '\t':
                    builder.Append("\\t");
                    break;
                default:
                    if (ch < 32)
                    {
                        builder.Append("\\u");
                        builder.Append(((int)ch).ToString("x4"));
                    }
                    else
                    {
                        builder.Append(ch);
                    }
                    break;
            }
        }
        return builder.ToString();
    }

    private static string FlattenException(Exception ex)
    {
        if (ex == null)
        {
            return null;
        }
        StringBuilder builder = new StringBuilder();
        Exception current = ex;
        while (current != null)
        {
            if (builder.Length > 0)
            {
                builder.Append(" | ");
            }
            builder.Append(current.GetType().FullName);
            builder.Append(": ");
            builder.Append(current.Message);
            current = current.InnerException;
        }
        return builder.ToString();
    }

    private static string SafeString(object value)
    {
        return value == null ? null : value.ToString();
    }

    private static void Trace(string message)
    {
        try
        {
            string directory = Path.GetDirectoryName(tracePath);
            if (!string.IsNullOrEmpty(directory))
            {
                Directory.CreateDirectory(directory);
            }
            File.AppendAllText(
                tracePath,
                DateTime.Now.ToString("HH:mm:ss.fff") + " " + message + Environment.NewLine,
                Encoding.UTF8);
        }
        catch
        {
        }
    }

    private static void TraceFormsSnapshot()
    {
        try
        {
            StringBuilder builder = new StringBuilder();
            builder.Append("forms=");
            builder.Append(Application.OpenForms.Count);
            int i;
            for (i = 0; i < Application.OpenForms.Count; i++)
            {
                Form form = Application.OpenForms[i];
                builder.Append("|");
                builder.Append(form.GetType().FullName);
                builder.Append(":");
                builder.Append(form.Text);
            }
            string snapshot = builder.ToString();
            if (snapshot != lastFormsSnapshot)
            {
                lastFormsSnapshot = snapshot;
                Trace(snapshot);
            }
        }
        catch
        {
        }
    }

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
    private static extern bool SetDllDirectory(string lpPathName);

    private delegate bool ConditionDelegate(Form mainForm);
}
