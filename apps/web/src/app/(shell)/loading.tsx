import { PageSkeleton } from "@/components/patterns/page-skeleton";

export default function ShellLoading() {
  return (
    <div className="p-6 md:p-8">
      <PageSkeleton />
    </div>
  );
}
