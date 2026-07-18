import type { Metadata } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "文脈特化型翻訳 | 鈴木トータルサービス",
  description:
    "ターゲット層に合わせて、テキスト・文書・画像を自然で伝わる表現へ翻訳する業務用AI翻訳ツール。",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ja" className={geistSans.variable}>
      <body>{children}</body>
    </html>
  );
}
