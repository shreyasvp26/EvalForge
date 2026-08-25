"use client";

import { Icon } from "../../icon/icon";
import { Search } from "../../icon/icons";
import { cn } from "../../lib/cn";
import { Input } from "../input/input";

import type { ChangeEvent } from "react";

export interface DataGridSearchProps {
  value: string;
  onValueChange: (value: string) => void;
  placeholder?: string;
  className?: string;
  id?: string;
}

/** Controlled search input wired to DataGrid `globalFilter`. */
export function DataGridSearch({
  value,
  onValueChange,
  placeholder = "Search…",
  className,
  id,
}: DataGridSearchProps) {
  return (
    <div className={cn("relative min-w-0 flex-1", className)}>
      <Icon
        icon={Search}
        size="sm"
        className="pointer-events-none absolute top-1/2 -translate-y-1/2 text-muted-foreground"
        style={{ left: 14 }}
        aria-hidden
      />
      <Input
        id={id}
        value={value}
        onChange={(event: ChangeEvent<HTMLInputElement>) => {
          onValueChange(event.target.value);
        }}
        placeholder={placeholder}
        aria-label={placeholder}
        className="pr-3"
        style={{ paddingLeft: 40 }}
      />
    </div>
  );
}
