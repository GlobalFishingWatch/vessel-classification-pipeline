package org.skytruth.common

import com.typesafe.scalalogging.{LazyLogging, Logger}
import org.joda.time.{DateTime, DateTimeZone}
import org.joda.time.format.ISODateTimeFormat
import scala.collection.{mutable, immutable}

object Implicits {
  implicit class RichLogger(val logger: Logger) {
    def fatal(message: String) = {
      logger.error(message)
      throw new RuntimeException(s"Fatal error: $message")
    }
  }

  implicit class RicherIterable[T](val iterable: Iterable[T]) {
    def countBy[K](fn: T => K): Map[K, Int] = {
      val counts = mutable.Map[K, Int]()
      iterable.foreach { el =>
        val k = fn(el)
        counts(k) = counts.getOrElse(k, 0) + 1
      }
      // Converts to immutable map.
      counts.toMap
    }

    // TODO(alexwilson): this is not a true median atm, because for an even
    // number of elements it does not average the two central values but picks
    // the lower arbitrarily. This is just to avoid having to have addition
    // and division also defined for T.
    def medianBy[V <% Ordered[V]](fn: T => V): T = {
      val asIndexedSeq = iterable.toIndexedSeq.sortBy(fn)
      asIndexedSeq.apply(asIndexedSeq.size / 2)
    }
  }
}

// TODO(alexwilson): This config is too hard-coded to our current setup. Move
// out to config files for greater flexibility. Note there is an equivalent to
// this in gcp_config.py which should remain in-sync.
object GcpConfig extends LazyLogging {
  import Implicits._

  private def projectId = "world-fishing-827"

  // TODO(alexwilson): No locally-generated date for prod. Needs to be sourced
  // from outside so all prod stages share the same path.
  def makeConfig(environment: String, jobId: String) = {
    val now = new DateTime(DateTimeZone.UTC)
    val rootPath = environment match {
      case "prod" => {
        s"gs://world-fishing-827/data-production/classification/$jobId"
      }
      case "dev" => {
        sys.env.get("USER") match {
          case Some(user) =>
            s"gs://world-fishing-827-dev-ttl30d/data-production/classification/$user/$jobId"
          case _ => logger.fatal("USER environment variable cannot be empty for dev runs.")
        }
      }
      case _ => logger.fatal(s"Invalid environment: $environment.")
    }

    GcpConfig(now, projectId, rootPath)
  }
}

case class GcpConfig(startTime: DateTime, projectId: String, private val rootPath: String) {
  def dataflowStagingPath = s"$rootPath/pipeline/staging"
  def pipelineOutputPath = s"$rootPath/pipeline/output"
}

case class IteratorWithCurrent[T](private val iterator: Iterator[T]) {
  private def nextOption(): Option[T] =
    if (iterator.hasNext) {
      Some(iterator.next)
    } else {
      None
    }

  var current: Option[T] = nextOption()

  def getNext() { current = nextOption() }
}