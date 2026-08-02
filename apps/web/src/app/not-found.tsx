import { Button, Heading, Stack, Text } from "@agent-eval/ui";
import Link from "next/link";

export default function NotFound() {
  return (
    <Stack gap={4} className="mx-auto max-w-lg px-6 py-24 text-center">
      <Text variant="caption" className="font-mono uppercase tracking-wide">
        404
      </Text>
      <Heading variant="page">Page not found</Heading>
      <Text variant="secondary">
        That route is not part of the EvalForge shell yet — or the URL is wrong.
      </Text>
      <div>
        <Button asChild variant="secondary">
          <Link href="/">Back to projects</Link>
        </Button>
      </div>
    </Stack>
  );
}
