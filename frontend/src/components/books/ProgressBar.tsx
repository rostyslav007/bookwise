interface ProgressBarProps {
  step: string;
}

export function ProgressBar({ step }: ProgressBarProps) {
  return (
    <div className="mt-2 flex items-center gap-2 rounded bg-amber-50 px-2 py-1 dark:bg-amber-950">
      <span className="inline-block h-2 w-2 animate-spin rounded-sm bg-amber-500" />
      <span className="text-xs text-amber-700 dark:text-amber-300">{step}</span>
    </div>
  );
}
