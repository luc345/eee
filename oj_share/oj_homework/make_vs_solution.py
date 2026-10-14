"""Generate a Visual Studio solution with one console project per OJ problem."""
import os, uuid, json

ROOT = r"C:\Users\<user>\WorkBuddy\<project>\oj_homework\code\cid1766"
SLN = os.path.join(ROOT, "OJ1766.sln")

PROJS = [
    ("A_seqlist_create", "A_seqlist_create.cpp"),
    ("B_seqlist_dearest", "B_seqlist_dearest.cpp"),
    ("C_linklist_create", "C_linklist_create.cpp"),
    ("D_linklist_sort", "D_linklist_sort.cpp"),
    ("E_linklist_merge", "E_linklist_merge.cpp"),
]

def guid_for(name):
    return "{" + str(uuid.uuid5(uuid.NAMESPACE_URL, "oj1766/" + name)).upper() + "}"

VCXPROJ = """<?xml version="1.0" encoding="utf-8"?>
<Project DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup Label="ProjectConfigurations">
    <ProjectConfiguration Include="Debug|x64">
      <Configuration>Debug</Configuration>
      <Platform>x64</Platform>
    </ProjectConfiguration>
    <ProjectConfiguration Include="Release|x64">
      <Configuration>Release</Configuration>
      <Platform>Release</Platform>
    </ProjectConfiguration>
  </ItemGroup>
  <PropertyGroup Label="Globals">
    <VCProjectVersion>17.0</VCProjectVersion>
    <ProjectGuid>%(guid)s</ProjectGuid>
    <RootNamespace>%(name)s</RootNamespace>
    <WindowsTargetPlatformVersion>10.0</WindowsTargetPlatformVersion>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.Default.props" />
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Debug|x64'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>true</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>
  <PropertyGroup Condition="'$(Configuration)|$(Platform)'=='Release|x64'" Label="Configuration">
    <ConfigurationType>Application</ConfigurationType>
    <UseDebugLibraries>false</UseDebugLibraries>
    <PlatformToolset>v145</PlatformToolset>
    <CharacterSet>Unicode</CharacterSet>
  </PropertyGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.props" />
  <ImportGroup Label="PropertySheets">
    <Import Project="$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props" Condition="exists('$(UserRootDir)\\Microsoft.Cpp.$(Platform).user.props')" Label="LocalAppDataPlatform" />
  </ImportGroup>
  <ItemDefinitionGroup>
    <ClCompile>
      <WarningLevel>Level3</WarningLevel>
      <LanguageStandard>stdcpp17</LanguageStandard>
      <AdditionalOptions>/utf-8 %%(AdditionalOptions)</AdditionalOptions>
    </ClCompile>
  </ItemDefinitionGroup>
  <ItemGroup>
    <ClCompile Include="..\\%(src)s" />
  </ItemGroup>
  <Import Project="$(VCTargetsPath)\\Microsoft.Cpp.targets" />
</Project>
"""

FILTERS = """<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <ItemGroup>
    <ClCompile Include="..\\%(src)s">
      <Filter>Source Files</Filter>
    </ClCompile>
  </ItemGroup>
  <ItemGroup>
    <Filter Include="Source Files">
      <UniqueIdentifier>%(fguid)s</UniqueIdentifier>
      <Extensions>cpp;c;cc;cxx</Extensions>
    </Filter>
  </ItemGroup>
</Project>
"""

CPP_GUID = "{8BC9CEB8-8B4A-11D0-8D11-00A0C91BC942}"

lines = []
lines.append("")
lines.append("Microsoft Visual Studio Solution File, Format Version 12.00")
lines.append("# Visual Studio Version 17")
lines.append("VisualStudioVersion = 17.0.31903.59")
lines.append("MinimumVisualStudioVersion = 10.0.40219.1")
for name, _ in PROJS:
    g = guid_for(name)
    lines.append('Project("%s") = "%s", "%s\\%s.vcxproj", "%s"' % (CPP_GUID, name, name, name, g))
    lines.append("EndProject")
lines.append("Global")
lines.append("\tGlobalSection(SolutionConfigurationPlatforms) = preSolution")
lines.append("\t\tDebug|x64 = Debug|x64")
lines.append("\t\tRelease|x64 = Release|x64")
lines.append("\tEndGlobalSection")
lines.append("\tGlobalSection(ProjectConfigurationPlatforms) = postSolution")
for name, _ in PROJS:
    g = guid_for(name)
    for cfg in ("Debug|x64", "Release|x64"):
        lines.append("\t\t%s.%s.ActiveCfg = %s" % (g, cfg, cfg))
        lines.append("\t\t%s.%s.Build.0 = %s" % (g, cfg, cfg))
lines.append("\tEndGlobalSection")
lines.append("\tGlobalSection(ExtensibilityGlobals) = postSolution")
lines.append("\t\tSolutionGuid = %s" % guid_for("__solution__"))
lines.append("\tEndGlobalSection")
lines.append("EndGlobal")

with open(SLN, "w", encoding="utf-8-sig", newline="\r\n") as f:
    f.write("\n".join(lines) + "\n")

for name, src in PROJS:
    d = os.path.join(ROOT, name)
    os.makedirs(d, exist_ok=True)
    ctx = {"guid": guid_for(name), "name": name, "src": src,
           "fguid": guid_for(name + "__filter")}
    with open(os.path.join(d, name + ".vcxproj"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(VCXPROJ % ctx)
    with open(os.path.join(d, name + ".vcxproj.filters"), "w", encoding="utf-8", newline="\r\n") as f:
        f.write(FILTERS % ctx)

print("solution:", SLN)
print("projects:", [p[0] for p in PROJS])
