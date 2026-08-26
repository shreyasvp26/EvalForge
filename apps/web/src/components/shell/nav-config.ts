import {
  BookOpen,
  Bot,
  CheckCircle2,
  FlaskConical,
  FolderKanban,
  LayoutDashboard,
  Layers,
  Play,
  Settings,
} from "@agent-eval/ui";

import type { LucideIcon } from "@agent-eval/ui";

export type NavHref =
  | "/"
  | "/projects"
  | "/benchmarks"
  | "/suites"
  | "/cases"
  | "/runs"
  | "/agents"
  | "/graders"
  | "/settings"
  | "/design-system";

export interface NavItem {
  href: NavHref;
  label: string;
  icon: LucideIcon;
  /** Chord shortcut hint, e.g. "G P" */
  chord?: string;
  keywords?: string[];
  /** Hide from primary product nav (still reachable via URL / command palette). */
  engineeringOnly?: boolean;
}

export interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

/**
 * Primary product navigation.
 * Suites/Cases remain reachable from project workspaces and command palette;
 * they are not top-level destinations (avoids orphaned project-scoped lists).
 */
export const navSections: NavSection[] = [
  {
    id: "workspace",
    label: "Workspace",
    items: [
      {
        href: "/",
        label: "Overview",
        icon: LayoutDashboard,
        chord: "G H",
        keywords: ["home", "dashboard", "overview", "workspace", "health"],
      },
      {
        href: "/projects",
        label: "Projects",
        icon: FolderKanban,
        chord: "G P",
        keywords: ["project", "create project", "workspace"],
      },
    ],
  },
  {
    id: "evaluation",
    label: "Evaluation",
    items: [
      {
        href: "/runs",
        label: "Runs",
        icon: Play,
        chord: "G R",
        keywords: ["run", "create run", "new run", "execution", "timeline"],
      },
      {
        href: "/benchmarks",
        label: "Benchmarks",
        icon: FlaskConical,
        chord: "G B",
        keywords: ["benchmark", "suite", "catalog", "coding benchmark"],
      },
      {
        href: "/agents",
        label: "Agents",
        icon: Bot,
        chord: "G A",
        keywords: ["agent", "adapter", "create agent"],
      },
      {
        href: "/graders",
        label: "Graders",
        icon: CheckCircle2,
        chord: "G G",
        keywords: ["grader", "objective", "rubric", "create grader", "score"],
      },
    ],
  },
  {
    id: "system",
    label: "System",
    items: [
      {
        href: "/settings",
        label: "Settings",
        icon: Settings,
        keywords: ["settings", "preferences", "profile", "account", "api", "about"],
      },
    ],
  },
];

/** Project-scoped resources — command palette / deep links only. */
export const secondaryNavItems: NavItem[] = [
  {
    href: "/suites",
    label: "Suites",
    icon: Layers,
    keywords: ["suite", "create suite", "composition"],
  },
  {
    href: "/cases",
    label: "Tasks",
    icon: FlaskConical,
    keywords: ["case", "task", "create case", "create task", "prompt", "specification"],
  },
  {
    href: "/design-system",
    label: "Design system",
    icon: BookOpen,
    keywords: ["tokens", "components", "gallery"],
    engineeringOnly: true,
  },
];

export const allNavItems: NavItem[] = [
  ...navSections.flatMap((section) => section.items),
  ...secondaryNavItems,
];

export const primaryNavItems: NavItem[] = navSections.flatMap((section) => section.items);

export function findNavItem(href: string): NavItem | undefined {
  return allNavItems.find((item) => item.href === href);
}

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/") return pathname === "/";
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function breadcrumbsForPath(pathname: string): { label: string; href?: string }[] {
  const crumbs: { label: string; href?: string }[] = [{ label: "EvalForge", href: "/" }];

  if (pathname === "/") {
    crumbs.push({ label: "Overview" });
    return crumbs;
  }

  if (pathname === "/projects") {
    crumbs.push({ label: "Projects" });
    return crumbs;
  }

  const projectMatch = /^\/projects\/([^/]+)(?:\/(.*))?$/.exec(pathname);
  if (projectMatch) {
    crumbs.push({ label: "Projects", href: "/projects" });
    const projectId = projectMatch[1] ?? "";
    const rest = projectMatch[2] ?? "";
    if (rest.startsWith("suites")) {
      crumbs.push({ label: "Project", href: `/projects/${projectId}` });
      const suiteRest = rest.slice("suites".length);
      if (suiteRest === "" || suiteRest === "/") {
        crumbs.push({ label: "Suites" });
      } else {
        crumbs.push({ label: "Suites", href: `/projects/${projectId}/suites` });
        crumbs.push({ label: "Suite" });
      }
      return crumbs;
    }
    if (rest.startsWith("benchmarks")) {
      crumbs.push({ label: "Project", href: `/projects/${projectId}` });
      const benchRest = rest.slice("benchmarks".length);
      if (benchRest === "" || benchRest === "/") {
        crumbs.push({ label: "Benchmarks" });
      } else {
        crumbs.push({ label: "Benchmarks", href: `/projects/${projectId}/benchmarks` });
        crumbs.push({ label: "Benchmark" });
      }
      return crumbs;
    }
    if (rest.startsWith("cases")) {
      crumbs.push({ label: "Project", href: `/projects/${projectId}` });
      const caseRest = rest.slice("cases".length);
      if (caseRest === "" || caseRest === "/") {
        crumbs.push({ label: "Tasks" });
      } else {
        crumbs.push({ label: "Tasks", href: `/projects/${projectId}/cases` });
        crumbs.push({ label: "Task" });
      }
      return crumbs;
    }
    crumbs.push({ label: "Project" });
    if (rest === "settings") {
      crumbs.push({ label: "Settings" });
    }
    return crumbs;
  }

  if (pathname === "/suites" || pathname === "/cases" || pathname === "/benchmarks") {
    crumbs.push({
      label: pathname === "/suites" ? "Suites" : pathname === "/cases" ? "Tasks" : "Benchmarks",
    });
    return crumbs;
  }

  const agentMatch = /^\/agents(?:\/(.*))?$/.exec(pathname);
  if (agentMatch) {
    const rest = agentMatch[1] ?? "";
    if (rest === "") {
      crumbs.push({ label: "Agents" });
      return crumbs;
    }
    crumbs.push({ label: "Agents", href: "/agents" });
    const adapterMatch = /^([^/]+)\/adapters\/([^/]+)$/.exec(rest);
    if (adapterMatch) {
      const nestedAgentId = adapterMatch[1] ?? "";
      crumbs.push({ label: "Agent", href: `/agents/${nestedAgentId}` });
      crumbs.push({ label: "Adapter" });
      return crumbs;
    }
    crumbs.push({ label: "Agent" });
    return crumbs;
  }

  const graderMatch = /^\/graders(?:\/(.*))?$/.exec(pathname);
  if (graderMatch) {
    const rest = graderMatch[1] ?? "";
    if (rest === "") {
      crumbs.push({ label: "Graders" });
      return crumbs;
    }
    crumbs.push({ label: "Graders", href: "/graders" });
    crumbs.push({ label: "Grader" });
    return crumbs;
  }

  const runMatch = /^\/runs(?:\/(.*))?$/.exec(pathname);
  if (runMatch) {
    const rest = runMatch[1] ?? "";
    if (rest === "") {
      crumbs.push({ label: "Runs" });
      return crumbs;
    }
    crumbs.push({ label: "Runs", href: "/runs" });
    if (rest === "new") {
      crumbs.push({ label: "New run" });
      return crumbs;
    }
    crumbs.push({ label: "Run" });
    return crumbs;
  }

  const settingsMatch = /^\/settings(?:\/(.*))?$/.exec(pathname);
  if (settingsMatch) {
    const rest = settingsMatch[1] ?? "";
    if (rest === "") {
      crumbs.push({ label: "Settings" });
      return crumbs;
    }
    crumbs.push({ label: "Settings", href: "/settings" });
    const labels: Record<string, string> = {
      profile: "Profile",
      account: "Account",
      preferences: "Preferences",
      providers: "Providers",
      github: "GitHub",
      api: "API",
      about: "About",
    };
    crumbs.push({ label: labels[rest] ?? "Page" });
    return crumbs;
  }

  if (pathname.startsWith("/design-system")) {
    crumbs.push({ label: "Design system" });
    return crumbs;
  }

  const match = allNavItems.find((item) => isNavActive(pathname, item.href));
  if (match) {
    crumbs.push({ label: match.label });
    return crumbs;
  }

  crumbs.push({ label: "Page" });
  return crumbs;
}
