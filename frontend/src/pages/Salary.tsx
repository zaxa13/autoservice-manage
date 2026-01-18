import { Container, Typography } from '@mui/material'

export default function Salary() {
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Зарплата
      </Typography>
      {/* Здесь будет компонент расчета зарплаты */}
    </Container>
  )
}

