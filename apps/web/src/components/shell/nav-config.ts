import { BookOpen, Bot, FlaskConical, FolderKanban, Layers, Play } from "@agent-eval/ui";

import type { LucideIcon } from "@agent-eval/ui";

export type NavHref = "/projects" | "/suites" | "/cases" | "/runs" | "/agents" | "/design-system";

export interface NavItem {
  href: NavHref;
  label: string;
  icon: LucideIcon;
  /** Chord shortcut hint, e.g. "G P" */
  chord?: string;
  keywords?: string[];
}

export interface NavSection {
  id: string;
  label: string;
  items: NavItem[];
}

export const navSections: NavSection[] = [
  {
    id: "workspace",
    label: "Workspace",
    items: [
      {
        href: "/projects",
        label: "Projects",
        icon: FolderKanban,
        chord: "G P",
        keywords: ["home", "workspace", "create project"],
      },
      {
        href: "/suites",
        label: "Suites",
        icon: Layers,
        keywords: ["suite", "create suite", "composition"],
      },
      {
        href: "/cases",
        label: "Cases",
        icon: FlaskConical,
        keywords: ["case", "create case", "prompt"],
      },
      { href: "/runs", label: "Runs", icon: Play, chord: "G R", keywords: ["run"] },
      {
        href: "/agents",
        label: "Agents",
        icon: Bot,
        chord: "G A",
        keywords: ["agent", "adapter", "create agent"],
      },
    ],
  },
  {
    id: "system",
    label: "System",
    items: [
      {
        href: "/design-system",
        label: "Design system",
        icon: BookOpen,
        keywords: ["tokens", "components", "gallery"],
      },
    ],
  },
];

export const allNavItems: NavItem[] = navSections.flatMap((section) => section.items);

export function findNavItem(href: string): NavItem | undefined {
  return allNavItems.find((item) => item.href === href);
}

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function breadcrumbsForPath(pathname: string): { label: string; href?: string }[] {
  const crumbs: { label: string; href?: string }[] = [{ label: "Workspace", href: "/projects" }];

  if (pathname === "/projects" || pathname === "/") {
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
    if (rest.startsWith("cases")) {
      crumbs.push({ label: "Project", href: `/projects/${projectId}` });
      const caseRest = rest.slice("cases".length);
      if (caseRest === "" || caseRest === "/") {
        crumbs.push({ label: "Cases" });
      } else {
        crumbs.push({ label: "Cases", href: `/projects/${projectId}/cases` });
        crumbs.push({ label: "Case" });
      }
      return crumbs;
    }
    crumbs.push({ label: "Project" });
    if (rest === "settings") {
      crumbs.push({ label: "Settings" });
    }
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

  const match = allNavItems.find((item) => isNavActive(pathname, item.href));
  if (match) {
    crumbs.push({ label: match.label });
    return crumbs;
  }

  crumbs.push({ label: "Page" });
  return crumbs;
}
