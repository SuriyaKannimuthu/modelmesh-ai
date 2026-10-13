"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const links = [
  { href: "/", label: "Overview" },
  { href: "/playground", label: "Playground" },
];

export function SiteHeader() {
  const pathname = usePathname();

  return (
    <header className="border-b border-black/[.08] bg-white dark:border-white/[.145] dark:bg-zinc-950">
      <div className="mx-auto flex h-14 w-full max-w-5xl items-center gap-8 px-4 sm:px-6">
        <Link href="/" className="font-semibold tracking-tight text-black dark:text-zinc-50">
          ModelMesh AI
        </Link>
        <nav className="flex gap-5 text-sm">
          {links.map(({ href, label }) => {
            const active = pathname === href;
            return (
              <Link
                key={href}
                href={href}
                aria-current={active ? "page" : undefined}
                className={
                  active
                    ? "font-medium text-black dark:text-zinc-50"
                    : "text-zinc-500 hover:text-black dark:hover:text-zinc-50"
                }
              >
                {label}
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
