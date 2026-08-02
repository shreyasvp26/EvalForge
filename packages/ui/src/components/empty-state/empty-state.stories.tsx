import { EmptyState } from "./empty-state";
import { Button } from "../button/button";
import { FolderKanban } from "../../icon/icons";

import type { Meta, StoryObj } from "@storybook/react";

const meta = {
  title: "Feedback/EmptyState",
  component: EmptyState,
  args: {
    icon: FolderKanban,
    title: "No projects yet",
    description: "Create a project to organize evaluation suites and runs.",
    action: <Button size="sm">New project</Button>,
  },
} satisfies Meta<typeof EmptyState>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Default: Story = {};
