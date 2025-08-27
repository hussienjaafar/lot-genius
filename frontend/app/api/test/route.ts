import { NextResponse } from "next/server";

export async function GET() {
  console.log("🔵 Test route GET called");
  return NextResponse.json({ message: "Test route works!" });
}

export async function POST() {
  console.log("🔵 Test route POST called");
  return NextResponse.json({ message: "Test route POST works!" });
}
