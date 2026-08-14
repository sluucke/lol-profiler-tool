export function ScreenHeader({ title }: { title: string }) {
  return (
    <h1 className="font-display text-sm font-bold tracking-[0.18em] text-app-text uppercase">{title}</h1>
  );
}
