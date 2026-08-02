import {
  Table,
  TableBody,
  TableCell,
  TableEmpty,
  TableHead,
  TableHeader,
  TableLoading,
  TableRow,
} from "./table";
import { Badge } from "../badge/badge";

import type { Meta, StoryObj } from "@storybook/react";

function DemoTable() {
  return (
    <div className="w-[640px]">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Run</TableHead>
            <TableHead>Agent</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          <TableRow tabIndex={0}>
            <TableCell className="font-mono text-[length:var(--ef-text-code)]">run_01</TableCell>
            <TableCell>Claude Code</TableCell>
            <TableCell>
              <Badge status="completed">Completed</Badge>
            </TableCell>
          </TableRow>
          <TableRow tabIndex={0}>
            <TableCell className="font-mono text-[length:var(--ef-text-code)]">run_02</TableCell>
            <TableCell>Codex</TableCell>
            <TableCell>
              <Badge status="running">Running</Badge>
            </TableCell>
          </TableRow>
        </TableBody>
      </Table>
    </div>
  );
}

const meta = {
  title: "Data/Table",
  component: DemoTable,
} satisfies Meta<typeof DemoTable>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
export const Loading: Story = {
  render: () => (
    <div className="w-[640px]">
      <TableLoading columns={3} rows={4} />
    </div>
  ),
};
export const Empty: Story = {
  render: () => (
    <div className="w-[640px]">
      <TableEmpty description="Adjust filters or create a new evaluation run." />
    </div>
  ),
};
