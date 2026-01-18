import { Container, Typography } from '@mui/material'

export default function Warehouse() {
  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        Склад
      </Typography>
      {/* Здесь будет компонент управления складом */}
    </Container>
  )
}

