-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: crossover.proxy.rlwy.net    Database: railway
-- ------------------------------------------------------
-- Server version	9.4.0

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `acertos_acerto`
--

DROP TABLE IF EXISTS `acertos_acerto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `acertos_acerto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `data_inicio` date NOT NULL,
  `data_fim` date NOT NULL,
  `data_geracao` datetime(6) NOT NULL,
  `total_viagens` int NOT NULL,
  `valor_total_viagens` decimal(10,2) NOT NULL,
  `total_vales` decimal(10,2) NOT NULL,
  `comissao` decimal(10,2) NOT NULL,
  `valor_a_receber` decimal(10,2) NOT NULL,
  `observacoes` longtext,
  `motorista_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `acertos_acerto_motorista_id_80033133_fk_motoristas_motorista_id` (`motorista_id`),
  KEY `acertos_acerto_usuario_id_154ccf5e_fk_register_user_id` (`usuario_id`),
  CONSTRAINT `acertos_acerto_motorista_id_80033133_fk_motoristas_motorista_id` FOREIGN KEY (`motorista_id`) REFERENCES `motoristas_motorista` (`id`),
  CONSTRAINT `acertos_acerto_usuario_id_154ccf5e_fk_register_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acertos_acerto`
--

LOCK TABLES `acertos_acerto` WRITE;
/*!40000 ALTER TABLE `acertos_acerto` DISABLE KEYS */;
INSERT INTO `acertos_acerto` VALUES (1,'2025-12-01','2025-12-29','2025-12-29 17:31:54.035724',7,51170.80,27065.00,6652.20,-20412.80,NULL,4,2),(2,'2025-11-01','2026-02-16','2026-01-05 16:21:28.010014',24,165260.34,27065.00,21483.84,-5581.16,NULL,4,2),(3,'2025-12-13','2025-12-31','2026-01-05 16:29:56.845279',4,27598.75,11600.00,3587.84,-8012.16,NULL,5,2);
/*!40000 ALTER TABLE `acertos_acerto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `acertos_itemacerto`
--

DROP TABLE IF EXISTS `acertos_itemacerto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `acertos_itemacerto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `data` date NOT NULL,
  `origem` varchar(255) NOT NULL,
  `destino` varchar(255) NOT NULL,
  `cliente` varchar(255) NOT NULL,
  `peso` decimal(10,2) NOT NULL,
  `valor_tonelada` decimal(10,2) NOT NULL,
  `valor_total` decimal(10,2) NOT NULL,
  `pago` tinyint(1) NOT NULL,
  `acerto_id` bigint NOT NULL,
  `viagem_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `acertos_itemacerto_acerto_id_7b681f05_fk_acertos_acerto_id` (`acerto_id`),
  KEY `acertos_itemacerto_viagem_id_3d2cd537_fk_viagens_viagem_id` (`viagem_id`),
  CONSTRAINT `acertos_itemacerto_acerto_id_7b681f05_fk_acertos_acerto_id` FOREIGN KEY (`acerto_id`) REFERENCES `acertos_acerto` (`id`),
  CONSTRAINT `acertos_itemacerto_viagem_id_3d2cd537_fk_viagens_viagem_id` FOREIGN KEY (`viagem_id`) REFERENCES `viagens_viagem` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=36 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acertos_itemacerto`
--

LOCK TABLES `acertos_itemacerto` WRITE;
/*!40000 ALTER TABLE `acertos_itemacerto` DISABLE KEYS */;
INSERT INTO `acertos_itemacerto` VALUES (1,'2025-12-01','Arcos','Coromandel','Não Informado',50.00,90.00,4500.00,0,1,16),(2,'2025-12-03','Coromandel','Piracema','Fazenda',50.30,180.00,9054.00,0,1,17),(3,'2025-12-06','Arcos','Monte Carmelo','Não Informado',50.00,80.00,4000.00,0,1,18),(4,'2025-12-08','Coromandel','Piracema','Fazenda',53.40,180.00,9612.00,0,1,30),(5,'2025-12-10','Coromandel','Piracema','Fazenda',50.56,180.00,9100.80,0,1,19),(6,'2025-12-12','Arcos','Catalão','Não Informado',50.00,108.00,5400.00,0,1,28),(7,'2025-12-16','Coromandel','Piracema','Fazenda',52.80,180.00,9504.00,0,1,29),(8,'2025-11-07','Coromandel','Piracema','Fazenda',39.19,180.00,7054.20,0,2,6),(9,'2025-11-07','Arcos','Monte Carmelo','Não Informado',35.70,65.00,2320.50,0,2,5),(10,'2025-11-11','Arcos','Ituiutaba','Não Informado',36.42,105.00,3824.10,0,2,7),(11,'2025-11-12','Uberlândia','Piracema','Fazenda',34.30,180.00,6174.00,0,2,8),(12,'2025-11-15','Coromandel','Piracema','Fazenda',39.08,180.00,7034.40,0,2,9),(13,'2025-11-17','Arcos','Catalão','Não Informado',50.00,110.00,5500.00,0,2,10),(14,'2025-11-18','Coromandel','Piracema','Fazenda',50.88,180.00,9158.40,0,2,11),(15,'2025-11-21','São Gotardo','Quirinópolis','Não Informado',50.00,120.00,6000.00,0,2,12),(16,'2025-11-24','Uberlândia','Piracema','Fazenda',49.60,180.00,8928.00,0,2,13),(17,'2025-11-26','Pains','São Gotardo','Não Informado',46.98,62.80,2950.34,0,2,14),(18,'2025-11-27','Coromandel','Piracema','Fazenda',51.59,180.00,9286.20,0,2,15),(19,'2025-12-01','Arcos','Coromandel','Não Informado',50.00,90.00,4500.00,0,2,16),(20,'2025-12-03','Coromandel','Piracema','Fazenda',50.30,180.00,9054.00,0,2,17),(21,'2025-12-06','Arcos','Monte Carmelo','Não Informado',50.00,80.00,4000.00,0,2,18),(22,'2025-12-08','Coromandel','Piracema','Fazenda',53.40,180.00,9612.00,0,2,30),(23,'2025-12-10','Coromandel','Piracema','Fazenda',50.56,180.00,9100.80,0,2,19),(24,'2025-12-12','Arcos','Catalão','Não Informado',50.00,108.00,5400.00,0,2,28),(25,'2025-12-16','Coromandel','Piracema','Fazenda',52.80,180.00,9504.00,0,2,29),(26,'2025-12-17','Coromandel','Piracema','Fazenda',49.02,180.00,8823.60,0,2,31),(27,'2025-12-22','Coromandel','Piracema','Fazenda',49.36,180.00,8884.80,0,2,32),(28,'2025-12-25','Arcos','Coromandel','Não Informado',50.00,90.00,4500.00,0,2,33),(29,'2025-12-29','Coromandel','Piracema','Fazenda',52.77,180.00,9498.60,0,2,34),(30,'2026-01-05','Arcos','Catalão','Não Informado',49.00,110.00,5390.00,0,2,35),(31,'2026-01-05','Uberlandia','Piracema','Fazenda',48.68,180.00,8762.40,0,2,36),(32,'2025-12-13','Uberlandia','Piracema','Fazenda',45.88,180.00,8258.40,0,3,37),(33,'2025-12-15','Perdizes','Uberlandia','Alfa',50.15,53.00,2657.95,0,3,38),(34,'2025-12-18','Uberlândia','Piracema','Fazenda',45.38,180.00,8168.40,0,3,39),(35,'2025-12-28','Uberlândia','Piracema','Fazenda',47.30,180.00,8514.00,0,3,40);
/*!40000 ALTER TABLE `acertos_itemacerto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `acertos_valeacerto`
--

DROP TABLE IF EXISTS `acertos_valeacerto`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `acertos_valeacerto` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `data` date NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `acerto_id` bigint NOT NULL,
  `vale_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `acertos_valeacerto_acerto_id_4d28a16f_fk_acertos_acerto_id` (`acerto_id`),
  KEY `acertos_valeacerto_vale_id_b8cf304c_fk_motoristas_vale_id` (`vale_id`),
  CONSTRAINT `acertos_valeacerto_acerto_id_4d28a16f_fk_acertos_acerto_id` FOREIGN KEY (`acerto_id`) REFERENCES `acertos_acerto` (`id`),
  CONSTRAINT `acertos_valeacerto_vale_id_b8cf304c_fk_motoristas_vale_id` FOREIGN KEY (`vale_id`) REFERENCES `motoristas_vale` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=6 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `acertos_valeacerto`
--

LOCK TABLES `acertos_valeacerto` WRITE;
/*!40000 ALTER TABLE `acertos_valeacerto` DISABLE KEYS */;
INSERT INTO `acertos_valeacerto` VALUES (1,'2025-12-16',23200.00,1,4),(2,'2025-12-16',3865.00,1,6),(3,'2025-12-16',23200.00,2,4),(4,'2025-12-16',3865.00,2,6),(5,'2025-12-08',11600.00,3,3);
/*!40000 ALTER TABLE `acertos_valeacerto` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group`
--

DROP TABLE IF EXISTS `auth_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(150) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group`
--

LOCK TABLES `auth_group` WRITE;
/*!40000 ALTER TABLE `auth_group` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_group_permissions`
--

DROP TABLE IF EXISTS `auth_group_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_group_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `group_id` int NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_group_permissions_group_id_permission_id_0cd325b0_uniq` (`group_id`,`permission_id`),
  KEY `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` (`permission_id`),
  CONSTRAINT `auth_group_permissio_permission_id_84c5c92e_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `auth_group_permissions_group_id_b120cbf9_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_group_permissions`
--

LOCK TABLES `auth_group_permissions` WRITE;
/*!40000 ALTER TABLE `auth_group_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `auth_group_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `auth_permission`
--

DROP TABLE IF EXISTS `auth_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_permission` (
  `id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(255) NOT NULL,
  `content_type_id` int NOT NULL,
  `codename` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `auth_permission_content_type_id_codename_01ab375a_uniq` (`content_type_id`,`codename`),
  CONSTRAINT `auth_permission_content_type_id_2f476e4b_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=73 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `auth_permission`
--

LOCK TABLES `auth_permission` WRITE;
/*!40000 ALTER TABLE `auth_permission` DISABLE KEYS */;
INSERT INTO `auth_permission` VALUES (1,'Can add log entry',1,'add_logentry'),(2,'Can change log entry',1,'change_logentry'),(3,'Can delete log entry',1,'delete_logentry'),(4,'Can view log entry',1,'view_logentry'),(5,'Can add permission',3,'add_permission'),(6,'Can change permission',3,'change_permission'),(7,'Can delete permission',3,'delete_permission'),(8,'Can view permission',3,'view_permission'),(9,'Can add group',2,'add_group'),(10,'Can change group',2,'change_group'),(11,'Can delete group',2,'delete_group'),(12,'Can view group',2,'view_group'),(13,'Can add content type',4,'add_contenttype'),(14,'Can change content type',4,'change_contenttype'),(15,'Can delete content type',4,'delete_contenttype'),(16,'Can view content type',4,'view_contenttype'),(17,'Can add session',5,'add_session'),(18,'Can change session',5,'change_session'),(19,'Can delete session',5,'delete_session'),(20,'Can view session',5,'view_session'),(21,'Can add user',6,'add_user'),(22,'Can change user',6,'change_user'),(23,'Can delete user',6,'delete_user'),(24,'Can view user',6,'view_user'),(25,'Can add caminhao',7,'add_caminhao'),(26,'Can change caminhao',7,'change_caminhao'),(27,'Can delete caminhao',7,'delete_caminhao'),(28,'Can view caminhao',7,'view_caminhao'),(29,'Can add carreta',8,'add_carreta'),(30,'Can change carreta',8,'change_carreta'),(31,'Can delete carreta',8,'delete_carreta'),(32,'Can view carreta',8,'view_carreta'),(33,'Can add motorista',9,'add_motorista'),(34,'Can change motorista',9,'change_motorista'),(35,'Can delete motorista',9,'delete_motorista'),(36,'Can view motorista',9,'view_motorista'),(37,'Can add vale',10,'add_vale'),(38,'Can change vale',10,'change_vale'),(39,'Can delete vale',10,'delete_vale'),(40,'Can view vale',10,'view_vale'),(41,'Can add viagem',11,'add_viagem'),(42,'Can change viagem',11,'change_viagem'),(43,'Can delete viagem',11,'delete_viagem'),(44,'Can view viagem',11,'view_viagem'),(45,'Can add categoria despesa',12,'add_categoriadespesa'),(46,'Can change categoria despesa',12,'change_categoriadespesa'),(47,'Can delete categoria despesa',12,'delete_categoriadespesa'),(48,'Can view categoria despesa',12,'view_categoriadespesa'),(49,'Can add despesa',13,'add_despesa'),(50,'Can change despesa',13,'change_despesa'),(51,'Can delete despesa',13,'delete_despesa'),(52,'Can view despesa',13,'view_despesa'),(53,'Can add funcionario despesa',14,'add_funcionariodespesa'),(54,'Can change funcionario despesa',14,'change_funcionariodespesa'),(55,'Can delete funcionario despesa',14,'delete_funcionariodespesa'),(56,'Can view funcionario despesa',14,'view_funcionariodespesa'),(57,'Can add lancamento mensal',15,'add_lancamentomensal'),(58,'Can change lancamento mensal',15,'change_lancamentomensal'),(59,'Can delete lancamento mensal',15,'delete_lancamentomensal'),(60,'Can view lancamento mensal',15,'view_lancamentomensal'),(61,'Can add vale acerto',18,'add_valeacerto'),(62,'Can change vale acerto',18,'change_valeacerto'),(63,'Can delete vale acerto',18,'delete_valeacerto'),(64,'Can view vale acerto',18,'view_valeacerto'),(65,'Can add acerto',16,'add_acerto'),(66,'Can change acerto',16,'change_acerto'),(67,'Can delete acerto',16,'delete_acerto'),(68,'Can view acerto',16,'view_acerto'),(69,'Can add item acerto',17,'add_itemacerto'),(70,'Can change item acerto',17,'change_itemacerto'),(71,'Can delete item acerto',17,'delete_itemacerto'),(72,'Can view item acerto',17,'view_itemacerto');
/*!40000 ALTER TABLE `auth_permission` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `caminhoes_caminhao`
--

DROP TABLE IF EXISTS `caminhoes_caminhao`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `caminhoes_caminhao` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome_conjunto` varchar(100) DEFAULT NULL,
  `placa_cavalo` varchar(10) DEFAULT NULL,
  `renavam_cavalo` varchar(20) DEFAULT NULL,
  `marca_modelo` varchar(200) DEFAULT NULL,
  `qtd_placas` int unsigned NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `caminhoes_caminhao_usuario_id_321f24f4_fk_register_user_id` (`usuario_id`),
  CONSTRAINT `caminhoes_caminhao_usuario_id_321f24f4_fk_register_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`),
  CONSTRAINT `caminhoes_caminhao_chk_1` CHECK ((`qtd_placas` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `caminhoes_caminhao`
--

LOCK TABLES `caminhoes_caminhao` WRITE;
/*!40000 ALTER TABLE `caminhoes_caminhao` DISABLE KEYS */;
INSERT INTO `caminhoes_caminhao` VALUES (4,'M.BENZ/ACTROS 2651S6X4','QQF1C57','01181496885',NULL,4,'2025-12-10 18:10:46.319251',2),(5,'Volvo/FH 560 6x4T','PYA3D20','01091906537',NULL,4,'2025-12-10 18:17:06.963658',2),(6,'Volvo/FH 440 6x2T','OCT5A34','00333347862',NULL,3,'2025-12-10 18:23:36.155654',2);
/*!40000 ALTER TABLE `caminhoes_caminhao` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `caminhoes_carreta`
--

DROP TABLE IF EXISTS `caminhoes_carreta`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `caminhoes_carreta` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `placa` varchar(10) DEFAULT NULL,
  `renavam` varchar(20) DEFAULT NULL,
  `caminhao_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `caminhoes_carreta_caminhao_id_aecdf84c_fk_caminhoes_caminhao_id` (`caminhao_id`),
  CONSTRAINT `caminhoes_carreta_caminhao_id_aecdf84c_fk_caminhoes_caminhao_id` FOREIGN KEY (`caminhao_id`) REFERENCES `caminhoes_caminhao` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=15 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `caminhoes_carreta`
--

LOCK TABLES `caminhoes_carreta` WRITE;
/*!40000 ALTER TABLE `caminhoes_carreta` DISABLE KEYS */;
INSERT INTO `caminhoes_carreta` VALUES (7,'QQM8A32','01186747061',4),(8,'QQM8A38','01186747193',4),(9,'QQM8A74','01186715763',4),(10,'GGQ2C79','01135291931',5),(11,'GDA9E09','01135285486',5),(12,'FYJ3F89','01135290366',5),(13,'ABD0J88','00900544333',6),(14,'ABD0C88','00900544341',6);
/*!40000 ALTER TABLE `caminhoes_carreta` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `despesas_categoriadespesa`
--

DROP TABLE IF EXISTS `despesas_categoriadespesa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `despesas_categoriadespesa` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome` varchar(100) NOT NULL,
  `descricao` longtext,
  `cor` varchar(7) NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `despesas_categoriadespesa_usuario_id_nome_57162684_uniq` (`usuario_id`,`nome`),
  CONSTRAINT `despesas_categoriade_usuario_id_aaf93657_fk_register_` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=23 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `despesas_categoriadespesa`
--

LOCK TABLES `despesas_categoriadespesa` WRITE;
/*!40000 ALTER TABLE `despesas_categoriadespesa` DISABLE KEYS */;
INSERT INTO `despesas_categoriadespesa` VALUES (1,'IPVA',NULL,'#6366F1',2),(2,'SEGURO',NULL,'#6366F1',2),(3,'LICENCIAMENTO',NULL,'#6366F1',2),(4,'RASTREADOR',NULL,'#6366F1',2),(5,'SALARIO',NULL,'#6366F1',2),(6,'COMISSAO',NULL,'#6366F1',2),(7,'MANUTENCAO',NULL,'#6366F1',2),(8,'MULTA',NULL,'#6366F1',2),(9,'GUINCHO',NULL,'#6366F1',2),(10,'FRANQUIA_SEGURO',NULL,'#6366F1',2),(11,'OUTROS',NULL,'#6366F1',2),(12,'IPVA',NULL,'#6366F1',4),(13,'SEGURO',NULL,'#6366F1',4),(14,'LICENCIAMENTO',NULL,'#6366F1',4),(15,'RASTREADOR',NULL,'#6366F1',4),(16,'SALARIO',NULL,'#6366F1',4),(17,'COMISSAO',NULL,'#6366F1',4),(18,'MANUTENCAO',NULL,'#6366F1',4),(19,'MULTA',NULL,'#6366F1',4),(20,'GUINCHO',NULL,'#6366F1',4),(21,'FRANQUIA_SEGURO',NULL,'#6366F1',4),(22,'OUTROS',NULL,'#6366F1',4);
/*!40000 ALTER TABLE `despesas_categoriadespesa` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `despesas_despesa`
--

DROP TABLE IF EXISTS `despesas_despesa`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `despesas_despesa` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `descricao` varchar(255) NOT NULL,
  `observacoes` longtext,
  `tipo` varchar(20) NOT NULL,
  `valor` decimal(12,2) NOT NULL,
  `competencia` date NOT NULL,
  `status` varchar(20) NOT NULL,
  `data_pagamento` date DEFAULT NULL,
  `data_vencimento` date DEFAULT NULL,
  `data_cadastro` datetime(6) NOT NULL,
  `data_atualizacao` datetime(6) NOT NULL,
  `caminhao_id` bigint NOT NULL,
  `categoria_id` bigint NOT NULL,
  `motorista_id` bigint DEFAULT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `despesas_despesa_caminhao_id_15b6cda6_fk_caminhoes_caminhao_id` (`caminhao_id`),
  KEY `despesas_despesa_motorista_id_3298520d_fk_motorista` (`motorista_id`),
  KEY `despesas_de_usuario_927bbc_idx` (`usuario_id`,`caminhao_id`,`tipo`),
  KEY `despesas_de_categor_52cab5_idx` (`categoria_id`,`status`),
  KEY `despesas_de_compete_3f68a0_idx` (`competencia`,`status`),
  CONSTRAINT `despesas_despesa_caminhao_id_15b6cda6_fk_caminhoes_caminhao_id` FOREIGN KEY (`caminhao_id`) REFERENCES `caminhoes_caminhao` (`id`),
  CONSTRAINT `despesas_despesa_categoria_id_5e2d67e7_fk_despesas_` FOREIGN KEY (`categoria_id`) REFERENCES `despesas_categoriadespesa` (`id`),
  CONSTRAINT `despesas_despesa_motorista_id_3298520d_fk_motorista` FOREIGN KEY (`motorista_id`) REFERENCES `motoristas_motorista` (`id`),
  CONSTRAINT `despesas_despesa_usuario_id_2f05f374_fk_register_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `despesas_despesa`
--

LOCK TABLES `despesas_despesa` WRITE;
/*!40000 ALTER TABLE `despesas_despesa` DISABLE KEYS */;
INSERT INTO `despesas_despesa` VALUES (1,'640L','','EVENTUAL',1000.00,'2025-12-09','PAGO','2025-12-29',NULL,'2025-12-29 17:02:19.482116','2025-12-29 17:02:32.596225',4,11,NULL,2);
/*!40000 ALTER TABLE `despesas_despesa` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_admin_log`
--

DROP TABLE IF EXISTS `django_admin_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_admin_log` (
  `id` int NOT NULL AUTO_INCREMENT,
  `action_time` datetime(6) NOT NULL,
  `object_id` longtext,
  `object_repr` varchar(200) NOT NULL,
  `action_flag` smallint unsigned NOT NULL,
  `change_message` longtext NOT NULL,
  `content_type_id` int DEFAULT NULL,
  `user_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `django_admin_log_content_type_id_c4bce8eb_fk_django_co` (`content_type_id`),
  KEY `django_admin_log_user_id_c564eba6_fk_register_user_id` (`user_id`),
  CONSTRAINT `django_admin_log_content_type_id_c4bce8eb_fk_django_co` FOREIGN KEY (`content_type_id`) REFERENCES `django_content_type` (`id`),
  CONSTRAINT `django_admin_log_user_id_c564eba6_fk_register_user_id` FOREIGN KEY (`user_id`) REFERENCES `register_user` (`id`),
  CONSTRAINT `django_admin_log_chk_1` CHECK ((`action_flag` >= 0))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_admin_log`
--

LOCK TABLES `django_admin_log` WRITE;
/*!40000 ALTER TABLE `django_admin_log` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_admin_log` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_content_type`
--

DROP TABLE IF EXISTS `django_content_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_content_type` (
  `id` int NOT NULL AUTO_INCREMENT,
  `app_label` varchar(100) NOT NULL,
  `model` varchar(100) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `django_content_type_app_label_model_76bd3d3b_uniq` (`app_label`,`model`)
) ENGINE=InnoDB AUTO_INCREMENT=19 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_content_type`
--

LOCK TABLES `django_content_type` WRITE;
/*!40000 ALTER TABLE `django_content_type` DISABLE KEYS */;
INSERT INTO `django_content_type` VALUES (16,'acertos','acerto'),(17,'acertos','itemacerto'),(18,'acertos','valeacerto'),(1,'admin','logentry'),(2,'auth','group'),(3,'auth','permission'),(7,'caminhoes','caminhao'),(8,'caminhoes','carreta'),(4,'contenttypes','contenttype'),(12,'despesas','categoriadespesa'),(13,'despesas','despesa'),(14,'despesas','funcionariodespesa'),(15,'despesas','lancamentomensal'),(9,'motoristas','motorista'),(10,'motoristas','vale'),(6,'register','user'),(5,'sessions','session'),(11,'viagens','viagem');
/*!40000 ALTER TABLE `django_content_type` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_migrations`
--

DROP TABLE IF EXISTS `django_migrations`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_migrations` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `app` varchar(255) NOT NULL,
  `name` varchar(255) NOT NULL,
  `applied` datetime(6) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=31 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_migrations`
--

LOCK TABLES `django_migrations` WRITE;
/*!40000 ALTER TABLE `django_migrations` DISABLE KEYS */;
INSERT INTO `django_migrations` VALUES (1,'contenttypes','0001_initial','2025-12-09 18:29:58.392246'),(2,'contenttypes','0002_remove_content_type_name','2025-12-09 18:29:58.526854'),(3,'auth','0001_initial','2025-12-09 18:29:58.933020'),(4,'auth','0002_alter_permission_name_max_length','2025-12-09 18:29:59.024292'),(5,'auth','0003_alter_user_email_max_length','2025-12-09 18:29:59.034369'),(6,'auth','0004_alter_user_username_opts','2025-12-09 18:29:59.041275'),(7,'auth','0005_alter_user_last_login_null','2025-12-09 18:29:59.052940'),(8,'auth','0006_require_contenttypes_0002','2025-12-09 18:29:59.057740'),(9,'auth','0007_alter_validators_add_error_messages','2025-12-09 18:29:59.066671'),(10,'auth','0008_alter_user_username_max_length','2025-12-09 18:29:59.076135'),(11,'auth','0009_alter_user_last_name_max_length','2025-12-09 18:29:59.090227'),(12,'auth','0010_alter_group_name_max_length','2025-12-09 18:29:59.102745'),(13,'auth','0011_update_proxy_permissions','2025-12-09 18:29:59.113618'),(14,'auth','0012_alter_user_first_name_max_length','2025-12-09 18:29:59.120197'),(15,'register','0001_initial','2025-12-09 18:29:59.608922'),(16,'admin','0001_initial','2025-12-09 18:29:59.830634'),(17,'admin','0002_logentry_remove_auto_add','2025-12-09 18:29:59.843726'),(18,'admin','0003_logentry_add_action_flag_choices','2025-12-09 18:29:59.857387'),(19,'caminhoes','0001_initial','2025-12-09 18:30:00.100979'),(20,'motoristas','0001_initial','2025-12-09 18:30:00.448255'),(21,'sessions','0001_initial','2025-12-09 18:30:00.504592'),(22,'viagens','0001_initial','2025-12-10 12:23:59.236869'),(23,'caminhoes','0002_remove_caminhao_crlv_cavalo_remove_carreta_crlv','2025-12-11 13:07:26.665171'),(29,'despesas','0001_initial','2025-12-29 16:57:33.865668'),(30,'acertos','0001_initial','2025-12-29 17:31:32.611205');
/*!40000 ALTER TABLE `django_migrations` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `django_session`
--

DROP TABLE IF EXISTS `django_session`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `django_session` (
  `session_key` varchar(40) NOT NULL,
  `session_data` longtext NOT NULL,
  `expire_date` datetime(6) NOT NULL,
  PRIMARY KEY (`session_key`),
  KEY `django_session_expire_date_a5c62663` (`expire_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `django_session`
--

LOCK TABLES `django_session` WRITE;
/*!40000 ALTER TABLE `django_session` DISABLE KEYS */;
/*!40000 ALTER TABLE `django_session` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `motoristas_motorista`
--

DROP TABLE IF EXISTS `motoristas_motorista`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `motoristas_motorista` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `nome` varchar(150) NOT NULL,
  `cpf` varchar(14) NOT NULL,
  `idade` int unsigned NOT NULL,
  `venc_cnh` date NOT NULL,
  `created_at` datetime(6) NOT NULL,
  `caminhao_id` bigint DEFAULT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `cpf` (`cpf`),
  KEY `motoristas_motorista_caminhao_id_808ccbaa_fk_caminhoes` (`caminhao_id`),
  KEY `motoristas_motorista_usuario_id_1a21af6d_fk_register_user_id` (`usuario_id`),
  CONSTRAINT `motoristas_motorista_caminhao_id_808ccbaa_fk_caminhoes` FOREIGN KEY (`caminhao_id`) REFERENCES `caminhoes_caminhao` (`id`),
  CONSTRAINT `motoristas_motorista_usuario_id_1a21af6d_fk_register_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`),
  CONSTRAINT `motoristas_motorista_chk_1` CHECK ((`idade` >= 0))
) ENGINE=InnoDB AUTO_INCREMENT=8 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `motoristas_motorista`
--

LOCK TABLES `motoristas_motorista` WRITE;
/*!40000 ALTER TABLE `motoristas_motorista` DISABLE KEYS */;
INSERT INTO `motoristas_motorista` VALUES (4,'Carlos Américo Silva','55761585634',59,'2028-08-06','2025-12-10 18:06:19.368403',4,2),(5,'Carlos Alberto Da Silva','04980202627',45,'2031-04-23','2025-12-10 18:25:35.406337',5,2),(6,'José Luiz dos Santos','93977700634',52,'2029-11-21','2025-12-16 21:12:05.678616',NULL,2),(7,'Rogério Ferreira Ribeiro','10990786609',33,'2032-11-29','2025-12-16 21:14:02.068422',6,2);
/*!40000 ALTER TABLE `motoristas_motorista` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `motoristas_vale`
--

DROP TABLE IF EXISTS `motoristas_vale`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `motoristas_vale` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `data` date NOT NULL,
  `valor` decimal(10,2) NOT NULL,
  `pago` tinyint(1) NOT NULL,
  `motorista_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `motoristas_vale_motorista_id_f6930f64_fk_motoristas_motorista_id` (`motorista_id`),
  CONSTRAINT `motoristas_vale_motorista_id_f6930f64_fk_motoristas_motorista_id` FOREIGN KEY (`motorista_id`) REFERENCES `motoristas_motorista` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `motoristas_vale`
--

LOCK TABLES `motoristas_vale` WRITE;
/*!40000 ALTER TABLE `motoristas_vale` DISABLE KEYS */;
INSERT INTO `motoristas_vale` VALUES (2,'2025-12-03',22800.00,1,4),(3,'2025-12-08',11600.00,0,5),(4,'2025-12-16',23200.00,0,4),(5,'2025-12-16',9243.00,0,7),(6,'2025-12-16',3865.00,0,4);
/*!40000 ALTER TABLE `motoristas_vale` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `register_user`
--

DROP TABLE IF EXISTS `register_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `register_user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `password` varchar(128) NOT NULL,
  `last_login` datetime(6) DEFAULT NULL,
  `is_superuser` tinyint(1) NOT NULL,
  `username` varchar(150) NOT NULL,
  `first_name` varchar(150) NOT NULL,
  `last_name` varchar(150) NOT NULL,
  `is_staff` tinyint(1) NOT NULL,
  `is_active` tinyint(1) NOT NULL,
  `date_joined` datetime(6) NOT NULL,
  `email` varchar(254) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `username` (`username`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `register_user`
--

LOCK TABLES `register_user` WRITE;
/*!40000 ALTER TABLE `register_user` DISABLE KEYS */;
INSERT INTO `register_user` VALUES (1,'pbkdf2_sha256$1200000$PzJqu67zgy8CQl9luWr9Z9$PW2HktJC1R6j99zUh8DEpaAlRzNmMz44yP/O9LjYCsA=',NULL,0,'dudu1','','',0,1,'2025-12-09 18:40:48.357191','dudu@1example.com'),(2,'pbkdf2_sha256$1200000$jthqis80qrvucwpR1UoSy7$pJ8ScHyZPOYIp7jkEBYcPoCO51v9bBSZ0z0umNvU5XM=',NULL,0,'Dudu','','',0,1,'2025-12-09 18:42:38.369677','dudu@example.com'),(3,'pbkdf2_sha256$1200000$1nQPzajLcKSWYr2tKGuG6X$FsSa497mTMe8yqS/uqteYlOkzP+QpSI8oPvcdxIx4WA=',NULL,0,'gILMAR','','',0,1,'2025-12-09 18:48:24.045202','gilmar@gilmar.com'),(4,'pbkdf2_sha256$1200000$2lFFqx9VvtwUABLEDhPCmQ$Esf98ipaMfmwqYVPIJI8D/l4EUw+mwiOSs+k155UdjU=',NULL,0,'Hueder','','',0,1,'2025-12-10 14:20:06.441050','hueder@example.com');
/*!40000 ALTER TABLE `register_user` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `register_user_groups`
--

DROP TABLE IF EXISTS `register_user_groups`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `register_user_groups` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `group_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `register_user_groups_user_id_group_id_29c2490d_uniq` (`user_id`,`group_id`),
  KEY `register_user_groups_group_id_ca93437c_fk_auth_group_id` (`group_id`),
  CONSTRAINT `register_user_groups_group_id_ca93437c_fk_auth_group_id` FOREIGN KEY (`group_id`) REFERENCES `auth_group` (`id`),
  CONSTRAINT `register_user_groups_user_id_c02a1648_fk_register_user_id` FOREIGN KEY (`user_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `register_user_groups`
--

LOCK TABLES `register_user_groups` WRITE;
/*!40000 ALTER TABLE `register_user_groups` DISABLE KEYS */;
/*!40000 ALTER TABLE `register_user_groups` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `register_user_user_permissions`
--

DROP TABLE IF EXISTS `register_user_user_permissions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `register_user_user_permissions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `permission_id` int NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `register_user_user_permi_user_id_permission_id_b0bd979f_uniq` (`user_id`,`permission_id`),
  KEY `register_user_user_p_permission_id_4888970d_fk_auth_perm` (`permission_id`),
  CONSTRAINT `register_user_user_p_permission_id_4888970d_fk_auth_perm` FOREIGN KEY (`permission_id`) REFERENCES `auth_permission` (`id`),
  CONSTRAINT `register_user_user_p_user_id_091bc010_fk_register_` FOREIGN KEY (`user_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `register_user_user_permissions`
--

LOCK TABLES `register_user_user_permissions` WRITE;
/*!40000 ALTER TABLE `register_user_user_permissions` DISABLE KEYS */;
/*!40000 ALTER TABLE `register_user_user_permissions` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `viagens_viagem`
--

DROP TABLE IF EXISTS `viagens_viagem`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `viagens_viagem` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `data` date NOT NULL,
  `origem` varchar(255) NOT NULL,
  `destino` varchar(255) NOT NULL,
  `cliente` varchar(255) NOT NULL,
  `peso` decimal(10,2) NOT NULL,
  `valor_tonelada` decimal(10,2) NOT NULL,
  `valor_total` decimal(10,2) NOT NULL,
  `pago` tinyint(1) NOT NULL,
  `motorista_id` bigint NOT NULL,
  `usuario_id` bigint NOT NULL,
  PRIMARY KEY (`id`),
  KEY `viagens_viagem_motorista_id_087d76b3_fk_motoristas_motorista_id` (`motorista_id`),
  KEY `viagens_viagem_usuario_id_32d7bb40_fk_register_user_id` (`usuario_id`),
  CONSTRAINT `viagens_viagem_motorista_id_087d76b3_fk_motoristas_motorista_id` FOREIGN KEY (`motorista_id`) REFERENCES `motoristas_motorista` (`id`),
  CONSTRAINT `viagens_viagem_usuario_id_32d7bb40_fk_register_user_id` FOREIGN KEY (`usuario_id`) REFERENCES `register_user` (`id`)
) ENGINE=InnoDB AUTO_INCREMENT=41 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `viagens_viagem`
--

LOCK TABLES `viagens_viagem` WRITE;
/*!40000 ALTER TABLE `viagens_viagem` DISABLE KEYS */;
INSERT INTO `viagens_viagem` VALUES (5,'2025-11-07','Arcos','Monte Carmelo','Não Informado',35.70,65.00,2320.50,0,4,2),(6,'2025-11-07','Coromandel','Piracema','Fazenda',39.19,180.00,7054.20,0,4,2),(7,'2025-11-11','Arcos','Ituiutaba','Não Informado',36.42,105.00,3824.10,0,4,2),(8,'2025-11-12','Uberlândia','Piracema','Fazenda',34.30,180.00,6174.00,0,4,2),(9,'2025-11-15','Coromandel','Piracema','Fazenda',39.08,180.00,7034.40,0,4,2),(10,'2025-11-17','Arcos','Catalão','Não Informado',50.00,110.00,5500.00,0,4,2),(11,'2025-11-18','Coromandel','Piracema','Fazenda',50.88,180.00,9158.40,0,4,2),(12,'2025-11-21','São Gotardo','Quirinópolis','Não Informado',50.00,120.00,6000.00,0,4,2),(13,'2025-11-24','Uberlândia','Piracema','Fazenda',49.60,180.00,8928.00,0,4,2),(14,'2025-11-26','Pains','São Gotardo','Não Informado',46.98,62.80,2950.34,0,4,2),(15,'2025-11-27','Coromandel','Piracema','Fazenda',51.59,180.00,9286.20,0,4,2),(16,'2025-12-01','Arcos','Coromandel','Não Informado',50.00,90.00,4500.00,0,4,2),(17,'2025-12-03','Coromandel','Piracema','Fazenda',50.30,180.00,9054.00,0,4,2),(18,'2025-12-06','Arcos','Monte Carmelo','Não Informado',50.00,80.00,4000.00,0,4,2),(19,'2025-12-10','Coromandel','Piracema','Fazenda',50.56,180.00,9100.80,0,4,2),(20,'2025-11-12','Santa Juliana','Piracema','Fazenda',46.90,160.00,7504.00,0,5,2),(21,'2025-11-14','Uberlândia','Piracema','Fazenda',47.04,180.00,8467.20,0,5,2),(22,'2025-11-19','Coromandel','Piracema','Fazenda',51.64,180.00,9295.20,0,5,2),(23,'2025-11-24','Uberlândia','Piracema','Fazenda',47.32,180.00,8517.60,0,5,2),(24,'2025-11-27','Arcos','Monte Alegre','Não Informado',46.99,85.00,3994.15,0,5,2),(25,'2025-11-28','Uberlândia','Piracema','Fazenda',47.50,180.00,8550.00,0,5,2),(26,'2025-12-02','Coromandel','Piracema','Fazenda',50.64,180.00,9115.20,0,5,2),(27,'2025-12-05','Uberlândia','Piracema','Fazenda',47.24,180.00,8503.20,0,5,2),(28,'2025-12-12','Arcos','Catalão','Não Informado',50.00,108.00,5400.00,0,4,2),(29,'2025-12-16','Coromandel','Piracema','Fazenda',52.80,180.00,9504.00,0,4,2),(30,'2025-12-08','Coromandel','Piracema','Fazenda',53.40,180.00,9612.00,0,4,2),(31,'2025-12-17','Coromandel','Piracema','Fazenda',49.02,180.00,8823.60,0,4,2),(32,'2025-12-22','Coromandel','Piracema','Fazenda',49.36,180.00,8884.80,0,4,2),(33,'2025-12-25','Arcos','Coromandel','Não Informado',50.00,90.00,4500.00,0,4,2),(34,'2025-12-29','Coromandel','Piracema','Fazenda',52.77,180.00,9498.60,0,4,2),(35,'2026-01-05','Arcos','Catalão','Não Informado',49.00,110.00,5390.00,0,4,2),(36,'2026-01-05','Uberlandia','Piracema','Fazenda',48.68,180.00,8762.40,0,4,2),(37,'2025-12-13','Uberlandia','Piracema','Fazenda',45.88,180.00,8258.40,0,5,2),(38,'2025-12-15','Perdizes','Uberlandia','Alfa',50.15,53.00,2657.95,0,5,2),(39,'2025-12-18','Uberlândia','Piracema','Fazenda',45.38,180.00,8168.40,0,5,2),(40,'2025-12-28','Uberlândia','Piracema','Fazenda',47.30,180.00,8514.00,0,5,2);
/*!40000 ALTER TABLE `viagens_viagem` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-08 10:42:04
