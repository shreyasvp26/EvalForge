"use client";

import { Button } from "../button/button";
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "../dropdown-menu/dropdown-menu";

import type { OnChangeFn, VisibilityState } from "@tanstack/react-table";

export interface DataGridColumnOption {
  id: string;
  label: string;
  canHide?: boolean;
}

export interface DataGridColumnVisibilityProps {
  columns: DataGridColumnOption[];
  visibility: VisibilityState;
  onVisibilityChange: OnChangeFn<VisibilityState>;
}

/** Column show/hide menu. Controlled via DataGrid `columnVisibility` state. */
export function DataGridColumnVisibility({
  columns,
  visibility,
  onVisibilityChange,
}: DataGridColumnVisibilityProps) {
  const hideable = columns.filter(
    (column) => column.canHide !== false && column.id !== "__actions",
  );

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button type="button" size="sm" variant="outline">
          Columns
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
        <DropdownMenuSeparator />
        {hideable.map((column) => {
          const visible = visibility[column.id] !== false;
          return (
            <DropdownMenuCheckboxItem
              key={column.id}
              checked={visible}
              onCheckedChange={(checked) => {
                onVisibilityChange((prev) => ({
                  ...prev,
                  [column.id]: checked,
                }));
              }}
            >
              {column.label}
            </DropdownMenuCheckboxItem>
          );
        })}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
