import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function ReviewTrend({ trends }: { trends: Record<string, number> }) {
  return <ResponsiveContainer width="100%" height={240}>
    <BarChart data={Object.entries(trends).map(([day, reviews]) => ({ day, reviews }))}>
      <CartesianGrid vertical={false} stroke="#263950"/>
      <XAxis dataKey="day" tick={{ fill: '#a1b3c9' }}/>
      <YAxis allowDecimals={false} tick={{ fill: '#a1b3c9' }}/>
      <Tooltip contentStyle={{ background: '#0d2035', borderColor: '#2d4964' }}/>
      <Bar dataKey="reviews" fill="#3de0c2" radius={[5, 5, 0, 0]} maxBarSize={48}/>
    </BarChart>
  </ResponsiveContainer>
}
