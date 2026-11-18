import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ReviewTrend({ trends }: { trends: Record<string, number> }) {
  return <ResponsiveContainer width="100%" height={240}>
    <BarChart data={Object.entries(trends).map(([day, reviews]) => ({ day, reviews }))}>
      <CartesianGrid vertical={false} stroke="var(--line)" strokeDasharray="4 4"/>
      <XAxis dataKey="day" tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={false} tickLine={false}/>
      <YAxis allowDecimals={false} tick={{ fill: 'var(--muted)', fontSize: 12 }} axisLine={false} tickLine={false}/>
      <Tooltip cursor={{ fill: 'var(--surface-raised)' }}
        contentStyle={{ background: 'var(--surface-inset)', borderColor: 'var(--control-border)', borderRadius: 'var(--radius-control)' }}
        labelStyle={{ color: 'var(--text)' }} itemStyle={{ color: 'var(--accent)' }}/>
      <Bar dataKey="reviews" fill="var(--accent)" radius={[5, 5, 0, 0]} maxBarSize={48}/>
    </BarChart>
  </ResponsiveContainer>
}
