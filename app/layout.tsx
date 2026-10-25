import type { Metadata } from 'next';
import { Archivo_Black, Inter } from 'next/font/google';
import './globals.css';

const display = Archivo_Black({
  variable: '--font-display',
  subsets: ['latin'],
  weight: '400',
});

const inter = Inter({
  variable: '--font-body',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'NAWI Lab — OIML R 76 Type Evaluation',
  description:
    'Controlled type-evaluation workspace for non-automatic weighing instruments.',
  icons: {
    icon: [
      { url: '/favicon.svg', type: 'image/svg+xml' },
      { url: '/favicon.ico', sizes: '32x32' },
    ],
    shortcut: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${inter.variable}`}>{children}</body>
    </html>
  );
}
