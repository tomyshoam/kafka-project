output "app_public_ip" {
  value = aws_instance.app.public_ip
}

output "app_url" {
  value = "http://${aws_instance.app.public_ip}:9000/ui"
}

output "kafka_private_ip" {
  value = aws_instance.kafka.private_ip
}

output "mongo_private_ip" {
  value = aws_instance.mongo.private_ip
}

output "ssm_targets" {
  value = {
    app   = aws_instance.app.id
    kafka = aws_instance.kafka.id
    mongo = aws_instance.mongo.id
  }
}
