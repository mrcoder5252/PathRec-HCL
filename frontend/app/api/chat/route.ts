import { gateway, streamText, convertToModelMessages, type UIMessage } from 'ai'

export async function POST(request: Request) {
  const body = await request.json() as { messages?: UIMessage[] }
  const messages = body.messages ?? []
  const result = streamText({
    model: gateway('openai/gpt-5-mini'),
    system: `You are NEXORA Copilot, a concise and encouraging AI career coach inside a student career operating system. Use this student context: Alex Morgan is a Computer Science student targeting Frontend Engineer roles. Readiness 72%, React 82%, communication 68%, system design 46%, data structures 39%, 3 active projects, 18.5 learning hours this month, interview average 81%. Give practical next steps, explain your reasoning, and never invent private records. Keep responses under 150 words unless asked for detail.`,
    messages: await convertToModelMessages(messages),
  })
  return result.toUIMessageStreamResponse()
}
